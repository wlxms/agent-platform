from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse
from fastapi.params import Depends

from agentp_shared.config import AUTH_URL, HOST_URL, MEMORY_URL, MARKET_URL, BILLING_URL
from agentp_shared.db import get_db
from agentp_shared.responses import data_response
from agentp_shared.event_bus import init_app_event_bus, shutdown_app_event_bus, Event, Topic
from .config import Settings
from .health import aggregate_health
from .proxy import get_task_status, proxy_request

settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    bus = await init_app_event_bus(app, "scheduler")

    # T8.3: subscribe to approval events
    if bus is not None:
        async def on_approval_requested(event: Event):
            pass  # Placeholder for auto-approve logic for admin orgs
        bus.subscribe(Topic.APPROVAL_REQUESTED, on_approval_requested)
        app.state.event_bus_task = asyncio.get_running_loop().create_task(bus.consume())

    yield
    await shutdown_app_event_bus(app)


app = FastAPI(
    title="OH Enterprise - Scheduler Service",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.service_name}


@app.get("/api/v1/tasks/{task_id}")
async def get_task(request: Request, task_id: str):
    request_id = request.headers.get("x-request-id", "")
    result = await get_task_status(task_id, request_id)
    return JSONResponse(content=result)


# Import approval module early so gateway-facing routes can use it
from . import approval as _approval_mod


# -----------------------------------------------------------------------
# Gateway-facing approval routes — MUST be registered before the
# catch-all ``/api/v1/{path:path}`` so they take priority.
# -----------------------------------------------------------------------

@app.post("/api/v1/approvals")
async def gw_create_approval(req: dict, request: Request, db=Depends(get_db)):
    org_id = req.get("org_id") or request.headers.get("x-org-id", "org-root")
    applicant_id = req.get("applicant_id") or request.headers.get("x-user-id", "")
    try:
        result = await _approval_mod.create_approval_request(
            db,
            org_id=org_id,
            applicant_id=applicant_id,
            template_name=req.get("template_name", ""),
            config_summary=req.get("config_summary"),
            reason=req.get("reason", ""),
        )
        return data_response(result)
    except _approval_mod.ApprovalError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "message": exc.message},
        )


@app.get("/api/v1/approvals")
async def gw_list_approvals(
    request: Request,
    org_id: str | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db=Depends(get_db),
):
    effective_org = org_id or request.headers.get("x-org-id", "org-root")
    return await _approval_mod.list_approvals(
        db, org_id=effective_org, status=status, page=page, page_size=page_size
    )


@app.post("/api/v1/approvals/{approval_id}/approve")
async def gw_approve_request(approval_id: str, req: dict, db=Depends(get_db)):
    try:
        result = await _approval_mod.approve_request(
            db, approval_id=approval_id, reviewer_id=req.get("reviewer_id", "")
        )
        return data_response(result)
    except _approval_mod.ApprovalError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "message": exc.message},
        )


@app.post("/api/v1/approvals/{approval_id}/reject")
async def gw_reject_request(approval_id: str, req: dict, db=Depends(get_db)):
    try:
        result = await _approval_mod.reject_request(
            db,
            approval_id=approval_id,
            reviewer_id=req.get("reviewer_id", ""),
            reason=req.get("reason", ""),
        )
        return data_response(result)
    except _approval_mod.ApprovalError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "message": exc.message},
        )


@app.get("/api/v1/approvals/history")
async def gw_approval_history(
    request: Request,
    org_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db=Depends(get_db),
):
    effective_org = org_id or request.headers.get("x-org-id", "org-root")
    return await _approval_mod.list_approvals(
        db, org_id=effective_org, status=None, page=page, page_size=page_size
    )


@app.api_route(
    "/api/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"]
)
async def api_router(request: Request, path: str):
    return await proxy_request(request, f"/api/v1/{path}")


@app.get("/internal/agents")
async def internal_agents_list(request: Request):
    return await proxy_request(request, "/api/v1/agents")


@app.post("/internal/agents")
async def internal_agents_create(request: Request):
    return await proxy_request(request, "/api/v1/agents")


@app.get("/internal/agents/{instance_id}")
async def internal_agents_get(request: Request, instance_id: str):
    return await proxy_request(request, f"/api/v1/agents/{instance_id}")


@app.delete("/internal/agents/{instance_id}")
async def internal_agents_delete(request: Request, instance_id: str):
    return await proxy_request(request, f"/api/v1/agents/{instance_id}")


@app.post("/internal/agents/{instance_id}/message")
async def internal_agents_message(request: Request, instance_id: str):
    return await proxy_request(request, f"/api/v1/agents/{instance_id}/message")


@app.get("/internal/health")
async def health_aggregation():
    result = await aggregate_health(
        services={
            "auth": AUTH_URL,
            "host": HOST_URL,
            "memory": MEMORY_URL,
            "market": MARKET_URL,
            "billing": BILLING_URL,
        }
    )
    overall = (
        "ok"
        if all(v["status"] == "ok" for v in result.values())
        else "degraded"
    )
    return data_response({"overall": overall, "services": result})


# ---------------------------------------------------------------------------
# Approval workflow (T5.2) — internal routes
# ---------------------------------------------------------------------------

@app.post("/internal/approvals")
async def create_approval(req: dict, db=Depends(get_db)):
    try:
        result = await _approval_mod.create_approval_request(
            db,
            org_id=req.get("org_id", ""),
            applicant_id=req.get("applicant_id", ""),
            template_name=req.get("template_name", ""),
            config_summary=req.get("config_summary"),
            reason=req.get("reason", ""),
        )
        return data_response(result)
    except _approval_mod.ApprovalError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "message": exc.message},
        )


@app.get("/internal/approvals")
async def list_approvals(
    org_id: str = Query(...),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db=Depends(get_db),
):
    return await _approval_mod.list_approvals(
        db, org_id=org_id, status=status, page=page, page_size=page_size
    )


@app.post("/internal/approvals/{approval_id}/approve")
async def approve_request(approval_id: str, req: dict, db=Depends(get_db)):
    try:
        result = await _approval_mod.approve_request(
            db, approval_id=approval_id, reviewer_id=req.get("reviewer_id", "")
        )
        return data_response(result)
    except _approval_mod.ApprovalError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "message": exc.message},
        )


@app.post("/internal/approvals/{approval_id}/reject")
async def reject_request(approval_id: str, req: dict, db=Depends(get_db)):
    try:
        result = await _approval_mod.reject_request(
            db,
            approval_id=approval_id,
            reviewer_id=req.get("reviewer_id", ""),
            reason=req.get("reason", ""),
        )
        return data_response(result)
    except _approval_mod.ApprovalError as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "message": exc.message},
        )


@app.get("/internal/approvals/history")
async def approval_history(
    org_id: str = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db=Depends(get_db),
):
    return await _approval_mod.list_approvals(
        db, org_id=org_id, status=None, page=page, page_size=page_size
    )

# ---------------------------------------------------------------------------
# Lifecycle management (T5.3)
# ---------------------------------------------------------------------------
from . import lifecycle as _lifecycle_mod
from fastapi.responses import JSONResponse as _JSONResp


@app.get("/internal/tasks/{task_id}")
async def get_task_status_route(task_id: str, db=Depends(get_db)):
    result = await _lifecycle_mod.get_task_status(db, task_id=task_id)
    if not result:
        return _JSONResp(
            status_code=404,
            content={"code": "NOT_FOUND", "message": f"Task {task_id} not found"},
        )
    return data_response(result)
