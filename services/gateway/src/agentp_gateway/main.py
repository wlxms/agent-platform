from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import Settings
from .middleware import GatewayMiddleware

settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="OH Enterprise - API Gateway",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(GatewayMiddleware)


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.service_name}
