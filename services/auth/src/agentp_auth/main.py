from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi.exceptions import RequestValidationError
from .config import Settings
from .api.v1.auth import router as auth_router, validation_exception_handler
from agentp_shared.db import async_session_factory
from . import service

settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Seed default data (root org, admin user, admin API key)
    async with async_session_factory() as db:
        await service.seed_default_data(db)
    yield


app = FastAPI(title="OH Enterprise - Auth", version="0.2.0", lifespan=lifespan)
app.include_router(auth_router)
app.add_exception_handler(RequestValidationError, validation_exception_handler)


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.service_name}
