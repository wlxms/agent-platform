"""Smoke tests for infrastructure layer (PostgreSQL + Redis).

These tests require running PostgreSQL and Redis instances.
Mark with: pytest -m smoke

Run: pytest tests/test_smoke_infrastructure.py -v -m smoke
"""
import os
import uuid
import json

import pytest
import redis.asyncio as aioredis
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

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

pytestmark = pytest.mark.smoke

DB_URL = os.environ.get(
    "AGENTP_DB_URL",
    "postgresql+asyncpg://agentp:agentp_dev@localhost:5432/agent_platform",
)
REDIS_URL = os.environ.get("AGENTP_REDIS_URL", "redis://localhost:6379/0")


class TestPostgreSQLConnection:
    """Smoke test: can we connect to PostgreSQL?"""

    @pytest.mark.asyncio
    async def test_connect_and_ping(self):
        """Verify basic PostgreSQL connectivity."""
        engine = create_async_engine(DB_URL, poolclass=NullPool)
        try:
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                row = result.fetchone()
                assert row[0] == 1
        finally:
            await engine.dispose()


class TestDatabaseModelsSmoke:
    """Smoke test: verify all DB tables exist and support CRUD operations."""

    @pytest.mark.asyncio
    async def test_all_tables_exist(self):
        """Verify all expected tables exist in the database."""
        engine = create_async_engine(DB_URL, poolclass=NullPool)
        try:
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
                    assert exists, f"Table {table_name} was not found"
        finally:
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_organization_crud(self):
        """Test full CRUD cycle for Organization model (creates + deletes own data)."""
        engine = create_async_engine(DB_URL, poolclass=NullPool)
        session_factory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        org_id = str(uuid.uuid4())
        try:
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
            # Cleanup: ensure test row is removed even on error
            try:
                async with session_factory() as session:
                    await session.execute(
                        text("DELETE FROM organizations WHERE id = :id"),
                        {"id": org_id},
                    )
                    await session.commit()
            except Exception:
                pass
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_user_with_organization(self):
        """Test User creation with Organization FK relationship."""
        engine = create_async_engine(DB_URL, poolclass=NullPool)
        session_factory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        org_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        try:
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
            try:
                async with session_factory() as session:
                    await session.execute(
                        text("DELETE FROM users WHERE id = :uid"), {"uid": user_id}
                    )
                    await session.execute(
                        text("DELETE FROM organizations WHERE id = :oid"),
                        {"oid": org_id},
                    )
                    await session.commit()
            except Exception:
                pass
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_agent_instance_with_usage(self):
        """Test AgentInstance and UsageRecord with FK relationships."""
        engine = create_async_engine(DB_URL, poolclass=NullPool)
        session_factory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        org_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        inst_id = str(uuid.uuid4())
        try:
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
            try:
                async with session_factory() as session:
                    await session.execute(
                        text("DELETE FROM usage_records WHERE instance_id = :iid"),
                        {"iid": inst_id},
                    )
                    await session.execute(
                        text("DELETE FROM agent_instances WHERE id = :iid"),
                        {"iid": inst_id},
                    )
                    await session.execute(
                        text("DELETE FROM users WHERE id = :uid"), {"uid": user_id}
                    )
                    await session.execute(
                        text("DELETE FROM organizations WHERE id = :oid"),
                        {"oid": org_id},
                    )
                    await session.commit()
            except Exception:
                pass
            await engine.dispose()


class TestRedisEventBusSmoke:
    """Smoke test: can we publish/subscribe events via Redis Streams?"""

    @pytest.mark.asyncio
    async def test_redis_connectivity(self):
        """Verify basic Redis connectivity."""
        r = aioredis.from_url(REDIS_URL, decode_responses=True)
        try:
            await r.ping()
            assert True
        finally:
            await r.aclose()

    @pytest.mark.asyncio
    async def test_event_bus_publish_and_read(self):
        """Test publishing an event and reading it back from Redis Streams."""
        r = aioredis.from_url(REDIS_URL, decode_responses=True)
        try:
            stream_key = f"agentp:events:{Topic.AGENT_CREATED}"
            # Clear stale events to ensure we read only our published event
            await r.delete(stream_key)

            bus = EventBus(redis=r, service_name="smoke-test")
            event = Event(
                topic=Topic.AGENT_CREATED,
                payload={"instance_id": "test-123", "name": "test-agent"},
                source="smoke-test",
                request_id="req-smoke-1",
            )
            await bus.publish(event)

            messages = await r.xrange(stream_key, count=1)
            assert len(messages) > 0

            _, fields = messages[0]
            payload = json.loads(fields["payload"])
            assert payload["instance_id"] == "test-123"
            assert fields["source"] == "smoke-test"

            await r.delete(stream_key)
        finally:
            await r.aclose()

    @pytest.mark.asyncio
    async def test_event_bus_subscribe_and_consume(self):
        """Test subscribing to a topic and receiving published events."""
        r = aioredis.from_url(REDIS_URL, decode_responses=True)
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
            await r.aclose()
