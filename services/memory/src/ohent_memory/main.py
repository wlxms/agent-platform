from fastapi import FastAPI

from .api.v1.assets import router as assets_router
from .config import Settings

settings = Settings()
app = FastAPI(title="OH Enterprise - Memory", version="0.1.0")
app.include_router(assets_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.service_name}
