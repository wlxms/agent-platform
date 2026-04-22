"""Redis Streams-based event bus for inter-service communication."""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Callable

from redis.asyncio import Redis

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

__all__ = [
    "Event",
    "Topic",
    "EventBus",
    "init_event_bus",
    "get_event_bus",
    "close_event_bus",
]


@dataclass
class Event:
    topic: str
    payload: dict
    source: str
    request_id: str


class Topic(StrEnum):
    AGENT_CREATED = "agent.created"
    AGENT_DESTROYED = "agent.destroyed"
    AGENT_STATUS_CHANGED = "agent.status_changed"
    AGENT_USAGE = "agent.usage"
    QUOTA_EXCEEDED = "quota.exceeded"
    APPROVAL_REQUESTED = "approval.requested"
    APPROVAL_APPROVED = "approval.approved"
    APPROVAL_REJECTED = "approval.rejected"
    PERMISSION_CHANGED = "permission.changed"
    BILLING_ALERT = "billing.alert"


class EventBus:
    def __init__(self, redis: Redis, service_name: str) -> None:
        self._redis = redis
        self._service_name = service_name
        self._handlers: dict[str, list[Callable]] = {}
        self._consumer_group = f"agentp-{service_name}"
        self._consumer_name = f"{service_name}-{id(self)}"
        self._task: asyncio.Task | None = None

    def subscribe(self, topic: str, handler: Callable) -> None:
        if topic not in self._handlers:
            self._handlers[topic] = []
        self._handlers[topic].append(handler)

    async def publish(self, event: Event) -> None:
        stream_key = f"agentp:events:{event.topic}"
        fields = {
            "payload": json.dumps(event.payload),
            "source": event.source,
            "request_id": event.request_id,
        }
        await self._redis.xadd(stream_key, fields, maxlen=10000, approximate=True)
        logger.debug("Published event %s to %s (request_id=%s)", event.topic, stream_key, event.request_id)

    async def consume(self) -> None:
        if not self._handlers:
            logger.warning("No handlers registered, consumer loop will not start")
            return

        stream_keys = {f"agentp:events:{topic}" for topic in self._handlers}

        for stream_key in stream_keys:
            try:
                await self._redis.xgroup_create(stream_key, self._consumer_group, id="0", mkstream=True)
            except Exception as exc:
                if "BUSYGROUP" in str(exc):
                    pass
                else:
                    raise

        self._task = asyncio.current_task()
        streams = ",".join(stream_keys)
        logger.info("Consumer loop started for service=%s, streams=%s", self._service_name, streams)

        while True:
            try:
                result = await self._redis.xreadgroup(
                    self._consumer_group,
                    self._consumer_name,
                    {key: ">" for key in stream_keys},
                    count=10,
                    block=1000,
                )
                if not result:
                    continue

                for stream_key, messages in result:
                    topic = stream_key.removeprefix("agentp:events:")
                    handlers = self._handlers.get(topic, [])

                    for message_id, message_data in messages:
                        for handler in handlers:
                            try:
                                payload = json.loads(message_data.get("payload", "{}"))
                                event = Event(
                                    topic=topic,
                                    payload=payload,
                                    source=message_data.get("source", ""),
                                    request_id=message_data.get("request_id", ""),
                                )
                                await handler(event)
                            except Exception:
                                logger.exception(
                                    "Handler error for topic=%s message_id=%s",
                                    topic,
                                    message_id,
                                )
                        try:
                            await self._redis.xack(stream_key, self._consumer_group, message_id)
                        except Exception:
                            logger.exception("XACK error for stream=%s message_id=%s", stream_key, message_id)

            except asyncio.CancelledError:
                logger.info("Consumer loop cancelled for service=%s", self._service_name)
                return

    async def close(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None


_bus: EventBus | None = None


def init_event_bus(redis: Redis, service_name: str) -> None:
    global _bus
    _bus = EventBus(redis, service_name)


def get_event_bus() -> EventBus:
    if _bus is None:
        raise RuntimeError("EventBus not initialized. Call init_event_bus() first.")
    return _bus


async def close_event_bus() -> None:
    global _bus
    if _bus is not None:
        await _bus.close()
        _bus = None


# ---------------------------------------------------------------------------
# FastAPI app.state helpers (preferred by M8)
# ---------------------------------------------------------------------------

async def init_app_event_bus(app, service_name: str, start_consumer: bool = False) -> EventBus:
    """Initialize EventBus via app.state (async, uses shared get_redis)."""
    from agentp_shared.redis import get_redis
    try:
        redis = await get_redis()
        bus = EventBus(redis=redis, service_name=service_name)
        app.state.event_bus = bus
        logger.info("EventBus initialized for service=%s", service_name)

        if start_consumer:
            app.state.event_bus_task = asyncio.get_running_loop().create_task(bus.consume())

        return bus
    except Exception:
        logger.warning("Failed to initialize EventBus for service=%s, continuing without it", service_name, exc_info=True)
        app.state.event_bus = None
        return None  # type: ignore[return-value]


async def shutdown_app_event_bus(app) -> None:
    """Stop consumer loop and close on shutdown."""
    bus = getattr(app.state, "event_bus", None)
    task = getattr(app.state, "event_bus_task", None)
    if task is not None:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        app.state.event_bus_task = None
    if bus is not None:
        await bus.close()
        app.state.event_bus = None
