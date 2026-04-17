from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api.v1.assets import router as assets_router
from .config import Settings
from . import service
from agentp_shared.db import async_session_factory

settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with async_session_factory() as db:
        await service.seed_default_data(db)
    yield


app = FastAPI(title="OH Enterprise - Memory", version="0.2.0", lifespan=lifespan)
app.include_router(assets_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.service_name}
