from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from pydantic import BaseModel

from agentp_shared.db import get_db
from agentp_host.service import HostService, HostError, sync_create_to_db, sync_destroy_in_db, list_instances_from_db, get_instance_from_db, seed_default_org
from agentp_shared.api_mapping import CreateAgentRequest
from agentp_shared.errors import OHError
from agentp_shared.event_bus import Event, Topic
from agentp_shared.responses import data_response

logger = logging.getLogger(__name__)

router = APIRouter()

_service: HostService | None = None

DEFAULT_ORG_ID = "org-root"
DEFAULT_USER_ID = "user-admin"


def get_service() -> HostService:
    global _service
    if _service is None:
        _service = HostService()
    return _service


@router.get("/internal/agents")
async def list_agents(db: AsyncSession = Depends(get_db)):
    result = await list_instances_from_db(db, org_id=DEFAULT_ORG_ID)
    return result


@router.post("/internal/agents")
async def create_agent(req: CreateAgentRequest, request: Request, db: AsyncSession = Depends(get_db)):
    svc = get_service()
    try:
        sdk_result = svc.create_instance(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": "INTERNAL_ERROR", "message": str(e)})

    # Sync to PostgreSQL
    try:
        await seed_default_org(db)
        await sync_create_to_db(
            db,
            instance_id=sdk_result["id"],
            name=req.name,
            org_id=DEFAULT_ORG_ID,
            user_id=DEFAULT_USER_ID,
            model=req.model or "",
            status=sdk_result.get("status", "created"),
        )
        await db.commit()
    except Exception as e:
        logger.warning("DB sync failed for create %s: %s", sdk_result["id"], e)
        # Don't fail the request — SDK create succeeded

    # T8.2: publish agent.created event
    bus = getattr(request.app.state, "event_bus", None)
    if bus is not None:
        try:
            await bus.publish(Event(
                topic=Topic.AGENT_CREATED,
                payload={"instance_id": sdk_result["id"], "org_id": DEFAULT_ORG_ID},
                source="host",
                request_id="",
            ))
        except Exception:
            logger.warning("Failed to publish agent.created event", exc_info=True)

    return {"data": sdk_result}


@router.get("/internal/agents/{instance_id}")
async def get_agent(instance_id: str, db: AsyncSession = Depends(get_db)):
    inst = await get_instance_from_db(db, instance_id=instance_id)
    if inst is None:
        err = OHError(code="NOT_FOUND", message=f"Instance not found: {instance_id}")
        raise HTTPException(status_code=err["status_code"], detail=err["detail"])
    return {"data": inst}


@router.delete("/internal/agents/{instance_id}")
async def destroy_agent(instance_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    svc = get_service()
    sdk_result = svc.destroy_instance(instance_id)

    # Sync status to PostgreSQL
    try:
        await sync_destroy_in_db(db, instance_id=instance_id)
        await db.commit()
    except Exception as e:
        logger.warning("DB sync failed for destroy %s: %s", instance_id, e)

    # T8.2: publish agent.destroyed event
    bus = getattr(request.app.state, "event_bus", None)
    if bus is not None:
        try:
            await bus.publish(Event(
                topic=Topic.AGENT_DESTROYED,
                payload={"instance_id": instance_id},
                source="host",
                request_id="",
            ))
        except Exception:
            logger.warning("Failed to publish agent.destroyed event", exc_info=True)

    return {"ok": True, "deleted": sdk_result}


@router.post("/internal/agents/{instance_id}/message")
async def send_message(instance_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    svc = get_service()
    prompt = body.get("prompt", "")
    model = body.get("model")
    try:
        result = svc.send_message(instance_id, prompt, model)
    except HostError as e:
        err = OHError(code=e.code, message=e.message)
        raise HTTPException(status_code=e.status_code, detail=err["detail"])
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": "INTERNAL_ERROR", "message": str(e)})
    return {"data": result}


# ---- T7.1: Restart / batch operations ----

class BatchIdsRequest(BaseModel):
    ids: list[str]


@router.post("/internal/agents/{agent_id}/restart")
async def restart_agent(agent_id: str):
    svc = get_service()
    try:
        result = svc.restart_instance(agent_id)
    except HostError as e:
        err = OHError(code=e.code, message=e.message)
        raise HTTPException(status_code=e.status_code, detail=err["detail"])
    return data_response(result)


@router.post("/internal/agents/batch-restart")
async def batch_restart(req: BatchIdsRequest):
    svc = get_service()
    result = svc.batch_restart(req.ids)
    return data_response(result)


@router.post("/internal/agents/batch-destroy")
async def batch_destroy(req: BatchIdsRequest):
    svc = get_service()
    result = svc.batch_destroy(req.ids)
    return data_response(result)


# ---- T7.2: Command execution ----

class CommandRequest(BaseModel):
    command: str


@router.post("/internal/agents/{agent_id}/command")
async def execute_command(agent_id: str, req: CommandRequest):
    svc = get_service()
    try:
        result = svc.execute_command(agent_id, req.command)
    except HostError as e:
        err = OHError(code=e.code, message=e.message)
        raise HTTPException(status_code=e.status_code, detail=err["detail"])
    return data_response(result)


# ---- T7.3: Skills / MCP / config management ----

class AddSkillRequest(BaseModel):
    skill_id: str


class AddMcpRequest(BaseModel):
    name: str
    transport: str
    config: dict | None = None


@router.post("/internal/agents/{agent_id}/skills")
async def add_skill(agent_id: str, req: AddSkillRequest):
    svc = get_service()
    result = svc.add_skill(agent_id, req.skill_id)
    return data_response(result)


@router.post("/internal/agents/{agent_id}/mcp")
async def add_mcp(agent_id: str, req: AddMcpRequest):
    svc = get_service()
    result = svc.add_mcp(agent_id, name=req.name, transport=req.transport, config=req.config)
    return data_response(result)


@router.put("/internal/agents/{agent_id}/config")
async def update_config(agent_id: str, req: dict):
    svc = get_service()
    result = svc.update_config(agent_id, **req)
    return data_response(result)


# ---- T7.4: Monitor / memory tree ----

@router.get("/internal/agents/{agent_id}/monitor")
async def get_monitor_stats(agent_id: str):
    svc = get_service()
    result = svc.get_monitor_stats(agent_id)
    return data_response(result)


@router.get("/internal/agents/{agent_id}/memory/tree")
async def get_memory_tree(agent_id: str):
    svc = get_service()
    result = svc.get_memory_tree(agent_id)
    return data_response(result)
