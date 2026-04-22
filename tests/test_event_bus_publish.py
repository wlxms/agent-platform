"""T8.2 — Verify Event creation for publishing on state changes."""
import pytest

from agentp_shared.event_bus import Event, Topic


async def test_publish_agent_created_event():
    event = Event(topic=Topic.AGENT_CREATED, payload={"instance_id": "i1", "name": "Test"}, source="host", request_id="req-1")
    assert event.topic == "agent.created"
    assert event.payload["instance_id"] == "i1"


async def test_publish_usage_event():
    event = Event(topic=Topic.AGENT_USAGE, payload={"tokens": 100, "cost": 0.001}, source="billing", request_id="req-2")
    assert event.topic == "agent.usage"
