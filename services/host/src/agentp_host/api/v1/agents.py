from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from agentp_shared.db import get_db
from agentp_host.service import HostService, HostError, sync_create_to_db, sync_destroy_in_db, list_instances_from_db, get_instance_from_db, seed_default_org
from agentp_shared.api_mapping import CreateAgentRequest
from agentp_shared.errors import OHError

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
async def create_agent(req: CreateAgentRequest, db: AsyncSession = Depends(get_db)):
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

    return {"data": sdk_result}


@router.get("/internal/agents/{instance_id}")
async def get_agent(instance_id: str, db: AsyncSession = Depends(get_db)):
    inst = await get_instance_from_db(db, instance_id=instance_id)
    if inst is None:
        err = OHError(code="NOT_FOUND", message=f"Instance not found: {instance_id}")
        raise HTTPException(status_code=err["status_code"], detail=err["detail"])
    return {"data": inst}


@router.delete("/internal/agents/{instance_id}")
async def destroy_agent(instance_id: str, db: AsyncSession = Depends(get_db)):
    svc = get_service()
    sdk_result = svc.destroy_instance(instance_id)

    # Sync status to PostgreSQL
    try:
        await sync_destroy_in_db(db, instance_id=instance_id)
        await db.commit()
    except Exception as e:
        logger.warning("DB sync failed for destroy %s: %s", instance_id, e)

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
