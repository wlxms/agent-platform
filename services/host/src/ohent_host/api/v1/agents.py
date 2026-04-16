from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ohent_host.service import HostService
from ohent_shared.api_mapping import CreateAgentRequest
from ohent_shared.errors import OHError

router = APIRouter()

_service: HostService | None = None


def get_service() -> HostService:
    global _service
    if _service is None:
        _service = HostService()
    return _service


@router.get("/internal/agents")
async def list_agents():
    svc = get_service()
    return svc.list_instances()


@router.post("/internal/agents")
async def create_agent(req: CreateAgentRequest):
    svc = get_service()
    try:
        return {"data": svc.create_instance(req)}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": "INTERNAL_ERROR", "message": str(e)})


@router.get("/internal/agents/{instance_id}")
async def get_agent(instance_id: str):
    svc = get_service()
    try:
        return svc.get_instance(instance_id)
    except Exception as e:
        err = OHError(code="NOT_FOUND", message=f"Instance not found: {instance_id}")
        raise HTTPException(status_code=err["status_code"], detail=err["detail"])


@router.delete("/internal/agents/{instance_id}")
async def destroy_agent(instance_id: str):
    svc = get_service()
    return svc.destroy_instance(instance_id)


@router.post("/internal/agents/{instance_id}/message")
async def send_message(instance_id: str, body: dict):
    svc = get_service()
    prompt = body.get("prompt", "")
    model = body.get("model")
    return svc.send_message(instance_id, prompt, model)
