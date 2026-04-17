"""Billing service tests — runs against REAL PostgreSQL.

Requires: PostgreSQL running, alembic upgrade head applied.
Run: pytest tests/test_billing.py -v
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from agentp_shared.config import db_settings
from agentp_shared.models import UsageRecord, Organization, User, AgentInstance
from agentp_billing import service

# Test engine with NullPool — no connection reuse across loops
_test_engine = create_async_engine(db_settings.url, echo=False, poolclass=NullPool)
_test_session_factory = async_sessionmaker(_test_engine, class_=AsyncSession, expire_on_commit=False)

_test_org_id = "org-root"
_test_user_id = "user-billing-seed"

# Monkeypatch shared engine so ASGI routes also use NullPool
import agentp_shared.db as _shared_db
_shared_db.engine = _test_engine
_shared_db.async_session_factory = async_sessionmaker(_test_engine, class_=AsyncSession, expire_on_commit=False)


# ---- Fixtures ----

@pytest.fixture
async def db():
    """Provide a fresh DB session per test. Seeds default data."""
    async with _test_session_factory() as session:
        await service.seed_default_data(session)
        await session.commit()
        yield session
        # Cleanup: delete non-seed usage records
        await session.execute(
            delete(UsageRecord).where(UsageRecord.org_id == _test_org_id)
        )
        await session.commit()


# ---- Health ----

@pytest.mark.asyncio
async def test_health():
    from agentp_billing.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["service"] == "billing"


# ---- Service-level tests ----

class TestCreateUsageRecord:

    @pytest.mark.asyncio
    async def test_create_basic(self, db):
        result = await service.create_usage_record(
            db,
            instance_id="inst-001",
            org_id=_test_org_id,
            user_id=_test_user_id,
            model="gpt-4",
            input_tokens=100,
            output_tokens=50,
        )
        assert result["input_tokens"] == 100
        assert result["output_tokens"] == 50
        assert result["cost"] > 0
        assert result["instance_name"] == "inst-001"
        assert "id" in result

    @pytest.mark.asyncio
    async def test_create_default_model(self, db):
        result = await service.create_usage_record(
            db,
            instance_id="inst-002",
            org_id=_test_org_id,
            user_id=_test_user_id,
            input_tokens=0,
            output_tokens=0,
        )
        assert result["model"] == ""


class TestGetSummary:

    @pytest.mark.asyncio
    async def test_summary_has_fields(self, db):
        result = await service.get_summary(db, org_id=_test_org_id)
        assert "total_tokens" in result
        assert "total_cost" in result
        assert "by_model" in result
        assert "daily_trend" in result

    @pytest.mark.asyncio
    async def test_summary_seeded_data(self, db):
        result = await service.get_summary(db, org_id=_test_org_id, period="all")
        assert result["total_tokens"] > 0
        assert result["total_cost"] > 0

    @pytest.mark.asyncio
    async def test_summary_by_model(self, db):
        result = await service.get_summary(db, org_id=_test_org_id, period="all")
        model_names = {e["model"] for e in result["by_model"]}
        assert "gpt-4" in model_names
        assert "gpt-3.5-turbo" in model_names
        for entry in result["by_model"]:
            assert "tokens" in entry
            assert "cost" in entry


class TestListRecords:

    @pytest.mark.asyncio
    async def test_list_seeded_records(self, db):
        result = await service.list_records(db, org_id=_test_org_id)
        assert result["total"] >= 5
        assert len(result["items"]) >= 5

    @pytest.mark.asyncio
    async def test_list_item_shape(self, db):
        result = await service.list_records(db, org_id=_test_org_id)
        item = result["items"][0]
        for key in ("id", "time", "instance_name", "model", "input_tokens", "output_tokens", "cost"):
            assert key in item

    @pytest.mark.asyncio
    async def test_filter_by_instance(self, db):
        result = await service.list_records(db, org_id=_test_org_id, instance_id="inst-001")
        assert result["total"] >= 1
        for item in result["items"]:
            assert item["instance_name"] == "inst-001"

    @pytest.mark.asyncio
    async def test_filter_by_model(self, db):
        result = await service.list_records(db, org_id=_test_org_id, model="gpt-4")
        assert result["total"] >= 1
        for item in result["items"]:
            assert item["model"] == "gpt-4"

    @pytest.mark.asyncio
    async def test_pagination(self, db):
        result = await service.list_records(db, org_id=_test_org_id, page=1, page_size=2)
        assert len(result["items"]) == 2
        assert result["total"] >= 5
        assert result["page"] == 1
        assert result["page_size"] == 2


# ---- API-level tests ----

class TestAPIRoutes:

    @pytest.fixture(autouse=True)
    async def _seed(self, db):
        """Ensure seed data exists before each API test."""
        # The db fixture seeds and the API tests use ASGI which goes through
        # the monkeypatched shared engine — same DB, so seed data is visible.
        pass

    @pytest.mark.asyncio
    async def test_api_summary(self):
        from agentp_billing.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/internal/billing/usage/summary?period=month")
            assert resp.status_code == 200
            data = resp.json()["data"]
            assert data["total_tokens"] > 0
            assert data["total_cost"] > 0

    @pytest.mark.asyncio
    async def test_api_records(self):
        from agentp_billing.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/internal/billing/usage/records")
            assert resp.status_code == 200
            body = resp.json()
            assert body["total"] >= 5
            assert len(body["items"]) >= 5

    @pytest.mark.asyncio
    async def test_api_filter_instance(self):
        from agentp_billing.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/internal/billing/usage/records?instance_id=inst-001")
            assert resp.status_code == 200
            body = resp.json()
            for item in body["items"]:
                assert item["instance_name"] == "inst-001"


@pytest.mark.asyncio
async def test_records_empty_filter():
    from agentp_billing.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/internal/billing/usage/records?instance_id=nonexistent")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["items"] == []
