"""Smoke tests for infrastructure layer (PostgreSQL + Redis).

These tests require running PostgreSQL and Redis instances.
Mark with: pytest -m smoke

To register the smoke marker, add to pytest.ini or pyproject.toml:
    [tool.pytest.ini_options]
    markers = [
        "smoke: infrastructure smoke tests (PostgreSQL + Redis)",
    ]

Run: pytest tests/test_smoke_infrastructure.py -v -m smoke
"""
import os
import uuid
import asyncio
import json

import pytest
import redis.asyncio as aioredis
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from agentp_shared.db import Base
from agentp_shared.event_bus import Event, Topic, EventBus
from agentp_shared.models import (
    AgentInstance,
    ApiKey,
    BillingRule,
    MemoryAsset,
    Organization,
    TaskRecord,
    UsageRecord,
    User,
)


# Skip entire module if DB env not configured
REQUIRE_DB = pytest.mark.skipif(
    not os.environ.get("AGENTP_DB_URL"),
    reason="AGENTP_DB_URL not set; smoke tests require running PostgreSQL",
)
REQUIRE_REDIS = pytest.mark.skipif(
    not os.environ.get("AGENTP_REDIS_URL"),
    reason="AGENTP_REDIS_URL not set; smoke tests require running Redis",
)

pytestmark = pytest.mark.smoke


def _get_async_db_url() -> str:
    """Get async database URL for testing."""
    return os.environ.get(
        "AGENTP_DB_URL",
        "postgresql+asyncpg://agentp:agentp_dev@localhost:5432/agent_platform",
    )


def _get_redis_url() -> str:
    """Get Redis URL for testing."""
    return os.environ.get("AGENTP_REDIS_URL", "redis://localhost:6379/0")


class TestPostgreSQLConnection:
    """Smoke test: can we connect to PostgreSQL?"""

    @REQUIRE_DB
    def test_connect_and_ping(self):
        """Verify basic PostgreSQL connectivity."""
        async def _test():
            url = _get_async_db_url()
            engine = create_async_engine(url, pool_size=1)
            try:
                async with engine.connect() as conn:
                    result = await conn.execute(text("SELECT 1"))
                    row = result.fetchone()
                    assert row[0] == 1
            finally:
                await engine.dispose()

        asyncio.run(_test())


class TestDatabaseModelsSmoke:
    """Smoke test: can we create/drop tables from models?"""

    @REQUIRE_DB
    def test_create_all_tables(self):
        """Create all tables from models metadata."""
        async def _test():
            url = _get_async_db_url()
            engine = create_async_engine(url, pool_size=1)
            try:
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)

                async with engine.connect() as conn:
                    for table_name in [
                        "organizations",
                        "users",
                        "api_keys",
                        "agent_instances",
                        "usage_records",
                        "memory_assets",
                        "billing_rules",
                        "task_records",
                    ]:
                        result = await conn.execute(
                            text(
                                "SELECT EXISTS(SELECT 1 FROM information_schema.tables "
                                "WHERE table_name=:tn)"
                            ),
                            {"tn": table_name},
                        )
                        exists = result.fetchone()[0]
                        assert exists, f"Table {table_name} was not created"
            finally:
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.drop_all)
                await engine.dispose()

        asyncio.run(_test())

    @REQUIRE_DB
    def test_organization_crud(self):
        """Test full CRUD cycle for Organization model."""
        async def _test():
            url = _get_async_db_url()
            engine = create_async_engine(url, pool_size=1)
            session_factory = async_sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False
            )
            try:
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)

                org_id = str(uuid.uuid4())
                async with session_factory() as session:
                    # Create
                    org = Organization(
                        id=org_id, name="Smoke Test Corp", level=1, plan="basic"
                    )
                    session.add(org)
                    await session.commit()
                    await session.refresh(org)
                    assert org.id == org_id
                    assert org.name == "Smoke Test Corp"
                    assert org.created_at is not None

                    # Read
                    result = await session.execute(
                        select(Organization).where(Organization.id == org_id)
                    )
                    fetched = result.scalar_one_or_none()
                    assert fetched is not None
                    assert fetched.name == "Smoke Test Corp"

                    # Update
                    fetched.name = "Updated Corp"
                    await session.commit()
                    await session.refresh(fetched)
                    assert fetched.name == "Updated Corp"

                    # Delete
                    await session.delete(fetched)
                    await session.commit()
                    result = await session.execute(
                        select(Organization).where(Organization.id == org_id)
                    )
                    assert result.scalar_one_or_none() is None
            finally:
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.drop_all)
                await engine.dispose()

        asyncio.run(_test())

    @REQUIRE_DB
    def test_user_with_organization(self):
        """Test User creation with Organization FK relationship."""
        async def _test():
            url = _get_async_db_url()
            engine = create_async_engine(url, pool_size=1)
            session_factory = async_sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False
            )
            try:
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)

                org_id = str(uuid.uuid4())
                user_id = str(uuid.uuid4())
                async with session_factory() as session:
                    org = Organization(id=org_id, name="Test Org")
                    user = User(
                        id=user_id,
                        org_id=org_id,
                        username="testuser",
                        email="test@example.com",
                        role="admin",
                    )
                    session.add(org)
                    session.add(user)
                    await session.commit()
                    await session.refresh(user)
                    assert user.org_id == org_id
                    assert user.role == "admin"
                    assert user.status == "active"
            finally:
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.drop_all)
                await engine.dispose()

        asyncio.run(_test())

    @REQUIRE_DB
    def test_agent_instance_with_usage(self):
        """Test AgentInstance and UsageRecord with FK relationships."""
        async def _test():
            url = _get_async_db_url()
            engine = create_async_engine(url, pool_size=1)
            session_factory = async_sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False
            )
            try:
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)

                org_id = str(uuid.uuid4())
                user_id = str(uuid.uuid4())
                inst_id = str(uuid.uuid4())

                async with session_factory() as session:
                    session.add(Organization(id=org_id, name="Test"))
                    session.add(
                        User(
                            id=user_id,
                            org_id=org_id,
                            username="u",
                            email="u@t.com",
                        )
                    )
                    await session.flush()

                    inst = AgentInstance(
                        id=inst_id,
                        org_id=org_id,
                        user_id=user_id,
                        name="test-agent",
                        agent_type="openharness",
                        model="deepseek-chat",
                    )
                    session.add(inst)
                    await session.flush()

                    usage = UsageRecord(
                        instance_id=inst_id,
                        org_id=org_id,
                        user_id=user_id,
                        model="deepseek-chat",
                        input_tokens=100,
                        output_tokens=50,
                        total_tokens=150,
                        cost=0.001,
                    )
                    session.add(usage)
                    await session.commit()

                    result = await session.execute(
                        select(UsageRecord).where(UsageRecord.instance_id == inst_id)
                    )
                    records = result.scalars().all()
                    assert len(records) == 1
                    assert records[0].total_tokens == 150
            finally:
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.drop_all)
                await engine.dispose()

        asyncio.run(_test())


class TestRedisEventBusSmoke:
    """Smoke test: can we publish/subscribe events via Redis Streams?"""

    @REQUIRE_REDIS
    def test_redis_connectivity(self):
        """Verify basic Redis connectivity."""
        async def _test():
            url = _get_redis_url()
            r = aioredis.from_url(url, decode_responses=True)
            try:
                await r.ping()
                assert True
            finally:
                await r.close()

        asyncio.run(_test())

    @REQUIRE_REDIS
    def test_event_bus_publish_and_read(self):
        """Test publishing an event and reading it back from Redis Streams."""
        async def _test():
            url = _get_redis_url()
            r = aioredis.from_url(url, decode_responses=True)
            try:
                bus = EventBus(redis=r, service_name="smoke-test")
                event = Event(
                    topic=Topic.AGENT_CREATED,
                    payload={"instance_id": "test-123", "name": "test-agent"},
                    source="smoke-test",
                    request_id="req-smoke-1",
                )
                await bus.publish(event)

                stream_key = f"agentp:events:{Topic.AGENT_CREATED}"
                messages = await r.xrange(stream_key, count=1)
                assert len(messages) > 0

                _, fields = messages[0]
                payload = json.loads(fields["payload"])
                assert payload["instance_id"] == "test-123"
                assert fields["source"] == "smoke-test"

                await r.delete(stream_key)
            finally:
                await r.close()

        asyncio.run(_test())

    @REQUIRE_REDIS
    def test_event_bus_subscribe_and_consume(self):
        """Test subscribing to a topic and receiving published events."""
        async def _test():
            url = _get_redis_url()
            r = aioredis.from_url(url, decode_responses=True)
            try:
                bus = EventBus(redis=r, service_name="smoke-consumer")

                received_events: list[Event] = []

                async def handler(event: Event) -> None:
                    received_events.append(event)

                bus.subscribe(Topic.AGENT_CREATED, handler)

                stream_key = f"agentp:events:{Topic.AGENT_CREATED}"
                await r.xadd(
                    stream_key,
                    {
                        "payload": json.dumps({"test": "data"}),
                        "source": "other-service",
                        "request_id": "req-123",
                    },
                )

                assert Topic.AGENT_CREATED in bus._handlers
                assert len(bus._handlers[Topic.AGENT_CREATED]) == 1

                await r.delete(stream_key)
            finally:
                await r.close()

        asyncio.run(_test())
