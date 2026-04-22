from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api.v1.templates import router as market_router, builder_router
from .config import Settings
from agentp_shared.event_bus import init_app_event_bus, shutdown_app_event_bus

settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_app_event_bus(app, "market")
    yield
    await shutdown_app_event_bus(app)


app = FastAPI(title="OH Enterprise - Market", version="0.1.0", lifespan=lifespan)
app.include_router(market_router)
app.include_router(builder_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.service_name}
