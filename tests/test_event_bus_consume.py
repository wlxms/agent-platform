"""T8.3 — Verify event subscription handler registration."""
import pytest

from agentp_shared.event_bus import EventBus, Event, Topic


class MockRedis:
    async def xadd(self, *a, **kw):
        pass


def test_subscribe_handler_registered():
    bus = EventBus(redis=MockRedis(), service_name="test")
    received = []

    async def handler(event):
        received.append(event)

    bus.subscribe(Topic.QUOTA_EXCEEDED, handler)
    assert Topic.QUOTA_EXCEEDED in bus._handlers
    assert len(bus._handlers[Topic.QUOTA_EXCEEDED]) == 1
