from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import Settings
from .api.v1.usage import router as billing_router
from . import service

settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    service.init_billing()
    yield


app = FastAPI(title="OH Enterprise - Billing", version="0.1.0", lifespan=lifespan)

app.include_router(billing_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.service_name}
