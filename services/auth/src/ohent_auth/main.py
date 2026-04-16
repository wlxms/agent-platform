from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import Settings
from .api.v1.auth import router as auth_router
from . import service

settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    service.init_api_keys()
    yield


app = FastAPI(title="OH Enterprise - Auth", version="0.1.0", lifespan=lifespan)

app.include_router(auth_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.service_name}
