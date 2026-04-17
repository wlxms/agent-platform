from contextlib import asynccontextmanager
import os

from fastapi import FastAPI

from .api.v1.agents import router as agents_router
from .config import Settings

# Ensure DS_API_KEY is set for SDK send_message (skeleton uses dummy)
if not os.environ.get("DS_API_KEY"):
    os.environ["DS_API_KEY"] = "sk-3aa4613249a34bc6a54d14f561ca7597"

settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="OH Enterprise - Host Service", version="0.2.0", lifespan=lifespan)
app.include_router(agents_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.service_name}
