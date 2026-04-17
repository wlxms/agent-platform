from contextlib import asynccontextmanager

from fastapi import FastAPI

from agentp_shared.db import async_session_factory
from .config import Settings
from .api.v1.usage import router as billing_router
from . import service

settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with async_session_factory() as db:
        await service.seed_default_data(db)
        await db.commit()
    yield


app = FastAPI(title="OH Enterprise - Billing", version="0.2.0", lifespan=lifespan)

app.include_router(billing_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.service_name}
