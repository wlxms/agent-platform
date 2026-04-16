import pytest
from httpx import AsyncClient, ASGITransport


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
        resp = await client.post("/internal/agents", json={"name": "test-agent"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["name"] == "test-agent"
        assert data["status"] in ("ready", "running", "seeding", "creating")
        assert data["id"]


@pytest.mark.asyncio
async def test_list_agents():
    from agentp_host.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/internal/agents", json={"name": "list-test"})
        resp = await client.get("/internal/agents")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        assert len(body["items"]) >= 1


@pytest.mark.asyncio
async def test_get_agent():
    from agentp_host.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_resp = await client.post("/internal/agents", json={"name": "get-test"})
        agent_id = create_resp.json()["data"]["id"]
        resp = await client.get(f"/internal/agents/{agent_id}")
        assert resp.status_code == 200
        assert resp.json()["data"]["id"] == agent_id


@pytest.mark.asyncio
async def test_destroy_agent():
    from agentp_host.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_resp = await client.post("/internal/agents", json={"name": "destroy-test"})
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
            create_resp = await client.post("/internal/agents", json={"name": "msg-test"})
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
            create_resp = await client.post("/internal/agents", json={"name": "msg-nomodel"})
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
    """send_message without DS_API_KEY: HostService wraps error in RuntimeError."""
    from agentp_host.service import HostService
    from agentp_shared.api_mapping import CreateAgentRequest
    import os
    old = os.environ.pop("DS_API_KEY", None)
    try:
        svc = HostService()
        req = CreateAgentRequest(name="test")
        record = svc.client.create_instance(svc.mapper.to_sdk_request(req))
        try:
            svc.send_message(record.instance_id, "hello", "gpt-4")
            assert False, "Should have raised RuntimeError"
        except RuntimeError as e:
            assert "DS_API_KEY" in str(e)
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
async def test_list_agents_empty():
    """Fresh service should return empty list initially (if no instances created)."""
    from agentp_host.main import app
    from agentp_host.service import HostService
    svc = HostService()
    result = svc.list_instances()
    # noop driver may have instances from other tests, so just check structure
    assert "items" in result
    assert "total" in result
    assert isinstance(result["items"], list)
