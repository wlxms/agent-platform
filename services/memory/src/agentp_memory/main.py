from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api.v1.assets import router as assets_router
from .config import Settings
from agentp_shared.event_bus import init_app_event_bus, shutdown_app_event_bus
from . import service
from agentp_shared.db import async_session_factory

settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_app_event_bus(app, "memory")
    async with async_session_factory() as db:
        await service.seed_default_data(db)
    yield
    await shutdown_app_event_bus(app)


app = FastAPI(title="OH Enterprise - Memory", version="0.2.0", lifespan=lifespan)
app.include_router(assets_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.service_name}
