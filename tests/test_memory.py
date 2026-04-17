"""Memory service tests — runs against REAL PostgreSQL.

Requires: PostgreSQL running, alembic upgrade head applied.
Run: pytest tests/test_memory.py -v
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from agentp_shared.config import db_settings
from agentp_shared.models import MemoryAsset, Organization
from agentp_memory import service

# Test engine with NullPool — no connection reuse across loops
_test_engine = create_async_engine(db_settings.url, echo=False, poolclass=NullPool)
_test_session_factory = async_sessionmaker(_test_engine, class_=AsyncSession, expire_on_commit=False)

# Monkeypatch the shared engine so ASGI routes (Depends(get_db)) also use NullPool.
# Without this, pytest-asyncio creates a new event loop per test, and pooled
# connections from the shared engine become stale across loops.
import agentp_shared.db as _shared_db
_shared_db.engine = _test_engine
_shared_db.async_session_factory = async_sessionmaker(_test_engine, class_=AsyncSession, expire_on_commit=False)

_test_org_id = "org-memory-test"

# ---- Fixtures ----

@pytest.fixture
async def db():
    """Provide a fresh DB session per test. Seeds default data + test org."""
    async with _test_session_factory() as session:
        # Ensure test org exists
        from sqlalchemy import select
        result = await session.execute(
            select(Organization).where(Organization.id == _test_org_id)
        )
        if result.scalar_one_or_none() is None:
            session.add(Organization(id=_test_org_id, name="Memory Test"))
            await session.flush()
        await service.seed_default_data(session)
        yield session
        # Cleanup test org assets
        await session.execute(
            delete(MemoryAsset).where(MemoryAsset.org_id == _test_org_id)
        )
        await session.commit()


# ---- Health ----

@pytest.mark.asyncio
async def test_health():
    from agentp_memory.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# ---- Service-level CRUD tests ----

class TestCreateAsset:

    @pytest.mark.asyncio
    async def test_create_basic(self, db):
        result = await service.create_asset(
            db, path="test/hello.txt", content="Hello", org_id=_test_org_id,
        )
        assert result["path"] == "test/hello.txt"
        assert result["content_type"] == "text/plain"
        assert result["size_bytes"] == 5
        assert "id" in result
        assert "created_at" in result

    @pytest.mark.asyncio
    async def test_create_with_custom_content_type(self, db):
        result = await service.create_asset(
            db, path="data.json", content="{}", content_type="application/json",
            org_id=_test_org_id,
        )
        assert result["content_type"] == "application/json"

    @pytest.mark.asyncio
    async def test_create_empty_path_raises(self, db):
        with pytest.raises(service.MemoryError) as exc_info:
            await service.create_asset(db, path="", org_id=_test_org_id)
        assert exc_info.value.code == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_create_whitespace_path_raises(self, db):
        with pytest.raises(service.MemoryError) as exc_info:
            await service.create_asset(db, path="   ", org_id=_test_org_id)
        assert exc_info.value.code == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_upsert_existing(self, db):
        await service.create_asset(
            db, path="test/upsert.txt", content="v1", org_id=_test_org_id,
        )
        result = await service.create_asset(
            db, path="test/upsert.txt", content="v2", content_type="text/markdown",
            org_id=_test_org_id,
        )
        assert result["content_type"] == "text/markdown"
        fetched = await service.get_asset(db, path="test/upsert.txt", org_id=_test_org_id)
        assert fetched is not None
        assert fetched["content"] == "v2"


class TestGetAsset:

    @pytest.mark.asyncio
    async def test_get_existing(self, db):
        await service.create_asset(
            db, path="test/get.txt", content="data", org_id=_test_org_id,
        )
        result = await service.get_asset(db, path="test/get.txt", org_id=_test_org_id)
        assert result is not None
        assert result["path"] == "test/get.txt"
        assert result["content"] == "data"

    @pytest.mark.asyncio
    async def test_get_not_found(self, db):
        result = await service.get_asset(
            db, path="nonexistent/file.txt", org_id=_test_org_id,
        )
        assert result is None


class TestListAssets:

    @pytest.mark.asyncio
    async def test_list_seeded_assets(self, db):
        result = await service.list_assets(db)
        assert result["total"] >= 3
        assert len(result["items"]) >= 3
        assert "page" in result
        assert "page_size" in result

    @pytest.mark.asyncio
    async def test_list_with_path_filter(self, db):
        await service.create_asset(
            db, path="docs/readme.md", content="# Docs", org_id=_test_org_id,
        )
        await service.create_asset(
            db, path="src/main.py", content="print('hi')", org_id=_test_org_id,
        )
        result = await service.list_assets(
            db, path_prefix="docs/", org_id=_test_org_id,
        )
        assert all(item["path"].startswith("docs/") for item in result["items"])

    @pytest.mark.asyncio
    async def test_list_empty_filter(self, db):
        result = await service.list_assets(
            db, path_prefix="zzz_no_match", org_id=_test_org_id,
        )
        assert result["items"] == []
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_list_pagination(self, db):
        for i in range(3):
            await service.create_asset(
                db, path=f"page/item_{i}.txt", content=f"content_{i}",
                org_id=_test_org_id,
            )
        p1 = await service.list_assets(
            db, path_prefix="page/", page=1, page_size=2, org_id=_test_org_id,
        )
        assert len(p1["items"]) == 2
        assert p1["total"] == 3
        p2 = await service.list_assets(
            db, path_prefix="page/", page=2, page_size=2, org_id=_test_org_id,
        )
        assert len(p2["items"]) == 1

    @pytest.mark.asyncio
    async def test_list_item_shape(self, db):
        await service.create_asset(
            db, path="shape/test.txt", content="x", org_id=_test_org_id,
        )
        result = await service.list_assets(
            db, path_prefix="shape/", org_id=_test_org_id,
        )
        item = result["items"][0]
        assert "path" in item
        assert "name" in item
        assert "type" in item
        assert "size" in item
        assert "content_type" in item
        assert item["name"] == "test.txt"
        assert item["type"] == "file"


class TestDeleteAsset:

    @pytest.mark.asyncio
    async def test_delete_existing(self, db):
        await service.create_asset(
            db, path="test/del.txt", content="bye", org_id=_test_org_id,
        )
        deleted = await service.delete_asset(db, path="test/del.txt", org_id=_test_org_id)
        assert deleted is True
        fetched = await service.get_asset(db, path="test/del.txt", org_id=_test_org_id)
        assert fetched is None

    @pytest.mark.asyncio
    async def test_delete_not_found(self, db):
        deleted = await service.delete_asset(
            db, path="nonexistent/gone.txt", org_id=_test_org_id,
        )
        assert deleted is False


# ---- API-level tests (via ASGITransport) ----

class TestAPIRoutes:
    """API tests go through FastAPI's Depends(get_db) — now using monkeypatched NullPool."""

    @pytest.mark.asyncio
    async def test_api_create_and_get(self):
        from agentp_memory.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/internal/memory/assets", json={
                "path": "api_crud/test.txt",
                "content": "API content",
                "content_type": "text/plain",
            })
            assert resp.status_code == 200
            data = resp.json()
            assert data["data"]["path"] == "api_crud/test.txt"
            assert "id" in data["data"]

    @pytest.mark.asyncio
    async def test_api_get_not_found(self):
        from agentp_memory.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/internal/memory/assets/nonexistent/api_file_999.txt")
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_api_delete_not_found(self):
        from agentp_memory.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.delete("/internal/memory/assets/nonexistent/gone_999.txt")
            assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_api_create_empty_path(self):
        from agentp_memory.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/internal/memory/assets", json={
                "path": "",
                "content": "test",
            })
            assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_api_list_with_filter(self):
        from agentp_memory.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/internal/memory/assets", params={"path": "zzz_no_match_api"})
            assert resp.status_code == 200
            data = resp.json()
            assert data["items"] == []
