from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from .config import Settings
from .api.v1.auth import router as auth_router
from agentp_shared.db import async_session_factory
from agentp_shared.event_bus import init_app_event_bus, shutdown_app_event_bus
from . import service

settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_app_event_bus(app, "auth")
    # Seed default data (root org, admin user, admin API key)
    async with async_session_factory() as db:
        await service.seed_default_data(db)
    yield
    await shutdown_app_event_bus(app)


app = FastAPI(title="OH Enterprise - Auth", version="0.2.0", lifespan=lifespan)
app.include_router(auth_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.service_name}
