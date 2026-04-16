"""Unit tests for agentp_shared event bus."""
import pytest
import asyncio
import json
from unittest.mock import AsyncMock


class TestEvent:
    def test_event_creation(self):
        from agentp_shared.event_bus import Event
        e = Event(topic="agent.created", payload={"id": "1"}, source="host", request_id="req-1")
        assert e.topic == "agent.created"
        assert e.payload == {"id": "1"}
        assert e.source == "host"
        assert e.request_id == "req-1"

    def test_event_dataclass(self):
        from agentp_shared.event_bus import Event
        from dataclasses import fields
        field_names = {f.name for f in fields(Event)}
        assert field_names == {"topic", "payload", "source", "request_id"}


class TestTopic:
    def test_all_core_topics_defined(self):
        from agentp_shared.event_bus import Topic
        expected = [
            "agent.created", "agent.destroyed", "agent.status_changed",
            "agent.usage", "quota.exceeded",
            "approval.requested", "approval.approved", "approval.rejected",
            "permission.changed", "billing.alert",
        ]
        for t in expected:
            assert t in [v.value for v in Topic], f"Missing topic: {t}"

    def test_topic_is_string(self):
        from agentp_shared.event_bus import Topic
        assert isinstance(Topic.AGENT_CREATED, str)
        assert Topic.AGENT_CREATED == "agent.created"


class TestEventExports:
    def test_all_exports(self):
        from agentp_shared.event_bus import Event, Topic, EventBus
        from agentp_shared.event_bus import init_event_bus, get_event_bus, close_event_bus
        assert Event is not None
        assert Topic is not None
        assert EventBus is not None


class TestEventBusPublish:
    """Test EventBus.publish with mocked Redis."""

    def _make_bus(self):
        from agentp_shared.event_bus import EventBus
        redis_mock = AsyncMock()
        bus = EventBus(redis=redis_mock, service_name="test-service")
        return bus, redis_mock

    def test_publish_calls_xadd(self):
        from agentp_shared.event_bus import Event
        bus, redis_mock = self._make_bus()
        event = Event(topic="agent.created", payload={"instance_id": "abc"}, source="host", request_id="req-1")

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(bus.publish(event))
        finally:
            loop.close()

        redis_mock.xadd.assert_called_once()
        call_args = redis_mock.xadd.call_args
        assert call_args[0][0] == "agentp:events:agent.created"
        fields = call_args[0][1]
        assert json.loads(fields["payload"]) == {"instance_id": "abc"}
        assert fields["source"] == "host"
        assert fields["request_id"] == "req-1"

    def test_publish_with_maxlen(self):
        from agentp_shared.event_bus import Event
        bus, redis_mock = self._make_bus()
        event = Event(topic="agent.usage", payload={}, source="host", request_id="r1")

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(bus.publish(event))
        finally:
            loop.close()

        call_kwargs = redis_mock.xadd.call_args[1]
        assert call_kwargs["maxlen"] == 10000
        assert call_kwargs["approximate"] is True


class TestEventBusSubscribe:
    def test_subscribe_registers_handler(self):
        from agentp_shared.event_bus import EventBus, Topic
        redis_mock = AsyncMock()
        bus = EventBus(redis=redis_mock, service_name="test")

        handler = lambda e: None
        bus.subscribe(Topic.AGENT_CREATED, handler)

        assert Topic.AGENT_CREATED in bus._handlers
        assert handler in bus._handlers[Topic.AGENT_CREATED]

    def test_subscribe_multiple_handlers(self):
        from agentp_shared.event_bus import EventBus, Topic
        redis_mock = AsyncMock()
        bus = EventBus(redis=redis_mock, service_name="test")

        h1 = lambda e: None
        h2 = lambda e: None
        bus.subscribe(Topic.AGENT_CREATED, h1)
        bus.subscribe(Topic.AGENT_CREATED, h2)

        assert len(bus._handlers[Topic.AGENT_CREATED]) == 2


class TestModuleSingleton:
    def test_get_event_bus_raises_before_init(self):
        import agentp_shared.event_bus as eb
        original = eb._bus
        try:
            eb._bus = None
            with pytest.raises(RuntimeError, match="not initialized"):
                eb.get_event_bus()
        finally:
            eb._bus = original

    def test_init_and_get_event_bus(self):
        import agentp_shared.event_bus as eb
        redis_mock = AsyncMock()
        original = eb._bus
        try:
            eb._bus = None
            eb.init_event_bus(redis_mock, "test-svc")
            bus = eb.get_event_bus()
            assert bus is not None
            assert bus._service_name == "test-svc"
        finally:
            eb._bus = original

    def test_close_event_bus(self):
        import agentp_shared.event_bus as eb
        redis_mock = AsyncMock()
        original = eb._bus
        try:
            eb._bus = None
            eb.init_event_bus(redis_mock, "test-svc")
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(eb.close_event_bus())
            finally:
                loop.close()
            assert eb._bus is None
        finally:
            eb._bus = original
