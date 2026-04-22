"""T8.1 — Verify EventBus instantiation and app.state helpers."""
import pytest

from agentp_shared.event_bus import EventBus, Event, Topic


class MockRedis:
    async def xadd(self, *a, **kw):
        pass


def test_event_bus_instantiation():
    bus = EventBus(redis=MockRedis(), service_name="test")
    assert bus._service_name == "test"
    assert hasattr(bus, "publish")
    assert hasattr(bus, "subscribe")


def test_init_app_event_bus_sets_state():
    """init_app_event_bus should set app.state.event_bus."""
    from unittest.mock import AsyncMock, patch
    from agentp_shared.event_bus import init_app_event_bus, shutdown_app_event_bus
    from fastapi import FastAPI
    import asyncio

    app = FastAPI()
    mock_redis = MockRedis()

    async def _run():
        with patch("agentp_shared.redis.get_redis", new_callable=AsyncMock, return_value=mock_redis):
            bus = await init_app_event_bus(app, "test-svc")
            assert hasattr(app.state, "event_bus")
            assert app.state.event_bus is not None
            assert app.state.event_bus._service_name == "test-svc"
            await shutdown_app_event_bus(app)
            assert app.state.event_bus is None

    asyncio.run(_run())
