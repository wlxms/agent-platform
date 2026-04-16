from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .config import Settings
from .proxy import get_task_status, proxy_request

settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


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
