from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI

from agentp_shared.db import async_session_factory
from agentp_shared.event_bus import init_app_event_bus, shutdown_app_event_bus, Event, Topic
from .config import Settings
from .api.v1.usage import router as billing_router
from .api.v1.routes import router as billing_extra_router
from . import service

settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    bus = await init_app_event_bus(app, "billing")

    # T8.3: subscribe to agent.usage events
    if bus is not None:
        async def on_agent_usage(event: Event):
            org_id = event.payload.get("org_id", "")
            if not org_id:
                return
            try:
                async with async_session_factory() as db:
                    budget = await service.get_budget(db, org_id=org_id)
                    if budget and budget.get("threshold", 0) > 0:
                        total_cost = (await service.get_summary(db, org_id=org_id)).get("total_cost", 0)
                        threshold = budget["threshold"]
                        if total_cost >= threshold * 0.8:
                            await bus.publish(Event(
                                topic=Topic.BILLING_ALERT,
                                payload={"org_id": org_id, "threshold": threshold, "current_cost": total_cost},
                                source="billing",
                                request_id=event.request_id,
                            ))
            except Exception:
                pass

        bus.subscribe(Topic.AGENT_USAGE, on_agent_usage)
        app.state.event_bus_task = asyncio.get_running_loop().create_task(bus.consume())

    async with async_session_factory() as db:
        await service.seed_default_data(db)
        await db.commit()
    yield
    await shutdown_app_event_bus(app)


app = FastAPI(title="OH Enterprise - Billing", version="0.2.0", lifespan=lifespan)

app.include_router(billing_router)
app.include_router(billing_extra_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.service_name}
