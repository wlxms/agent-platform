from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api.v1.templates import router as market_router
from .config import Settings
from .service import MarketService

settings = Settings()
_service = MarketService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="OH Enterprise - Market", version="0.1.0", lifespan=lifespan)
app.include_router(market_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.service_name}
