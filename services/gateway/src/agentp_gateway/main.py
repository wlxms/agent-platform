from contextlib import asynccontextmanager
import os

from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import Settings
from .middleware import GatewayMiddleware
from agentp_shared.event_bus import init_app_event_bus, shutdown_app_event_bus

settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_app_event_bus(app, "gateway")
    yield
    await shutdown_app_event_bus(app)


app = FastAPI(
    title="OH Enterprise - API Gateway",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware (before GatewayMiddleware so it runs first)
cors_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:5174")
cors_origins = [origin.strip() for origin in cors_origins_str.split(",") if origin.strip()]
# When allow_credentials is True, we cannot use ["*"] - must use explicit origins
if "*" in cors_origins or not cors_origins:
    cors_origins = ["*"]
    allow_creds = False
else:
    allow_creds = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=allow_creds,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GatewayMiddleware)

router = APIRouter()


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.service_name}


@router.get("/api/v1/agents/{agent_id}/stream")
async def websocket_stub(agent_id: str):
    from agentp_shared.errors import error_response
    return JSONResponse(
        status_code=501,
        content=error_response("NOT_IMPLEMENTED", "WebSocket streaming is not yet implemented"),
    )

app.include_router(router)
