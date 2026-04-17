"""Tests for Host service — runs against REAL PostgreSQL via ASGI.

Requires: PostgreSQL running, alembic upgrade head applied.
Run: pytest tests/test_host.py -v
"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from agentp_shared.config import db_settings
from agentp_shared.models import AgentInstance, Organization, User

# Test engine with NullPool — no connection reuse across loops
_test_engine = create_async_engine(db_settings.url, echo=False, poolclass=NullPool)

# Monkeypatch shared engine so ASGI routes also use NullPool
import agentp_shared.db as _shared_db
_shared_db.engine = _test_engine
_shared_db.async_session_factory = async_sessionmaker(_test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True)
def _reset_host_service():
    """Reset global HostService singleton so each test gets a fresh instance."""
    import agentp_host.api.v1.agents as _mod
    _mod._service = None
    yield
    _mod._service = None


@pytest.mark.asyncio
async def test_health():
    from agentp_host.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_create_agent():
    from agentp_host.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/internal/agents", json={"name": f"test-agent-{uuid.uuid4().hex[:8]}"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["name"].startswith("test-agent-")
        assert data["status"] in ("ready", "running", "seeding", "creating")
        assert data["id"]


@pytest.mark.asyncio
async def test_list_agents():
    from agentp_host.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/internal/agents", json={"name": f"list-test-{uuid.uuid4().hex[:8]}"})
        resp = await client.get("/internal/agents")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        assert len(body["items"]) >= 1
        for item in body["items"]:
            assert "id" in item
            assert "name" in item
            assert "status" in item


@pytest.mark.asyncio
async def test_get_agent():
    from agentp_host.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_resp = await client.post("/internal/agents", json={"name": f"get-test-{uuid.uuid4().hex[:8]}"})
        agent_id = create_resp.json()["data"]["id"]
        resp = await client.get(f"/internal/agents/{agent_id}")
        assert resp.status_code == 200
        assert resp.json()["data"]["id"] == agent_id


@pytest.mark.asyncio
async def test_destroy_agent():
    from agentp_host.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_resp = await client.post("/internal/agents", json={"name": f"destroy-test-{uuid.uuid4().hex[:8]}"})
        agent_id = create_resp.json()["data"]["id"]
        resp = await client.delete(f"/internal/agents/{agent_id}")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_send_message():
    from agentp_host.main import app
    import os
    os.environ["DS_API_KEY"] = "sk-3aa4613249a34bc6a54d14f561ca7597"
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            create_resp = await client.post("/internal/agents", json={"name": f"msg-test-{uuid.uuid4().hex[:8]}"})
            agent_id = create_resp.json()["data"]["id"]
            resp = await client.post(
                f"/internal/agents/{agent_id}/message",
                json={"prompt": "hello", "model": "gpt-4"},
            )
            assert resp.status_code == 200
            data = resp.json()["data"]
            assert data["instance_id"] == agent_id
            assert "reply_text" in data
    finally:
        os.environ.pop("DS_API_KEY", None)


@pytest.mark.asyncio
async def test_send_message_no_model():
    from agentp_host.main import app
    import os
    os.environ["DS_API_KEY"] = "sk-3aa4613249a34bc6a54d14f561ca7597"
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            create_resp = await client.post("/internal/agents", json={"name": f"msg-nomodel-{uuid.uuid4().hex[:8]}"})
            agent_id = create_resp.json()["data"]["id"]
            resp = await client.post(
                f"/internal/agents/{agent_id}/message",
                json={"prompt": "hello"},
            )
            assert resp.status_code == 200
            assert resp.json()["data"]["instance_id"] == agent_id
    finally:
        os.environ.pop("DS_API_KEY", None)


@pytest.mark.asyncio
async def test_send_message_no_api_key():
    """send_message without DS_API_KEY should return 502."""
    from agentp_host.main import app
    import os
    old = os.environ.pop("DS_API_KEY", None)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            create_resp = await client.post("/internal/agents", json={"name": f"msg-nokey-{uuid.uuid4().hex[:8]}"})
            agent_id = create_resp.json()["data"]["id"]
            resp = await client.post(
                f"/internal/agents/{agent_id}/message",
                json={"prompt": "hello", "model": "gpt-4"},
            )
            # SDK error propagates as 502 via HostError
            assert resp.status_code in (500, 502)
    finally:
        if old is not None:
            os.environ["DS_API_KEY"] = old


@pytest.mark.asyncio
async def test_get_agent_not_found():
    from agentp_host.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/internal/agents/nonexistent-id")
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_agents_structure():
    """List endpoint should return proper pagination structure."""
    from agentp_host.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/internal/agents")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "total" in body
        assert "page" in body
        assert "page_size" in body
        assert isinstance(body["items"], list)
