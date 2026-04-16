"""Tests for the Scheduler service - proxy routing, task status, error handling."""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_health():
    from ohent_scheduler.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_task_status_unknown():
    """Unknown task returns completed with null result."""
    from ohent_scheduler.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/tasks/task-123")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["id"] == "task-123"
        assert data["status"] == "completed"
        assert data["result"] is None


@pytest.mark.asyncio
async def test_task_status_known():
    """Known task returns stored data."""
    from ohent_scheduler.proxy import _tasks
    from ohent_scheduler.main import app

    _tasks["task-abc"] = {"id": "task-abc", "status": "running", "result": None}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/tasks/task-abc")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "running"

    _tasks.pop("task-abc", None)


@pytest.mark.asyncio
async def test_proxy_agents_to_host():
    """GET /api/v1/agents forwards to host service."""
    from ohent_scheduler.main import app

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"items": [], "total": 0, "page": 1, "page_size": 20}

    with patch("ohent_scheduler.proxy.httpx.AsyncClient") as mock_client_cls:
        mock_instance = AsyncMock()
        mock_instance.request = AsyncMock(return_value=mock_response)
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_cm

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                "/api/v1/agents",
                headers={"x-request-id": "req-1", "x-user-id": "u-1", "x-org-id": "o-1"},
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["total"] == 0

            # Verify the proxy called the host backend with rewritten path
            call_kwargs = mock_instance.request.call_args
            assert call_kwargs.kwargs["method"] == "GET"
            assert "/internal/agents" in call_kwargs.kwargs["url"]


@pytest.mark.asyncio
async def test_proxy_auth_forward():
    """POST /api/v1/auth/login forwards to auth service."""
    from ohent_scheduler.main import app

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"access_token": "tok", "token_type": "bearer"}

    with patch("ohent_scheduler.proxy.httpx.AsyncClient") as mock_client_cls:
        mock_instance = AsyncMock()
        mock_instance.request = AsyncMock(return_value=mock_response)
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_cm

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/auth/login",
                json={"username": "admin", "password": "pass"},
                headers={"x-request-id": "req-2"},
            )
            assert resp.status_code == 200
            call_kwargs = mock_instance.request.call_args
            assert "/internal/auth/login" in call_kwargs.kwargs["url"]


@pytest.mark.asyncio
async def test_proxy_memory_forward():
    """GET /api/v1/memory/stores forwards to memory service."""
    from ohent_scheduler.main import app

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"items": [], "total": 0}

    with patch("ohent_scheduler.proxy.httpx.AsyncClient") as mock_client_cls:
        mock_instance = AsyncMock()
        mock_instance.request = AsyncMock(return_value=mock_response)
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_cm

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                "/api/v1/memory/stores",
                headers={"x-request-id": "req-3"},
            )
            assert resp.status_code == 200
            call_kwargs = mock_instance.request.call_args
            assert "/internal/memory/stores" in call_kwargs.kwargs["url"]


@pytest.mark.asyncio
async def test_proxy_headers_forwarded():
    """Verify internal headers are set on forwarded requests."""
    from ohent_scheduler.main import app

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {}

    with patch("ohent_scheduler.proxy.httpx.AsyncClient") as mock_client_cls:
        mock_instance = AsyncMock()
        mock_instance.request = AsyncMock(return_value=mock_response)
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_cm

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                "/api/v1/billing/plans",
                headers={"x-request-id": "rid-1", "x-user-id": "uid-1", "x-org-id": "oid-1"},
            )
            assert resp.status_code == 200

            call_kwargs = mock_instance.request.call_args
            headers = call_kwargs.kwargs["headers"]
            assert headers["X-Request-ID"] == "rid-1"
            assert headers["X-User-ID"] == "uid-1"
            assert headers["X-Tenant-ID"] == "oid-1"
            assert headers["X-Org-ID"] == "oid-1"
            assert headers["X-Internal-Call"] == "true"


@pytest.mark.asyncio
async def test_proxy_upstream_unavailable():
    """502 when backend connection fails."""
    from ohent_scheduler.main import app

    with patch("ohent_scheduler.proxy.httpx.AsyncClient") as mock_client_cls:
        mock_instance = AsyncMock()
        mock_instance.request.side_effect = Exception("Connection refused")
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_cm

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                "/api/v1/agents",
                headers={"x-request-id": "req-err"},
            )
            assert resp.status_code == 502
            body = resp.json()
            assert body["code"] == "UPSTREAM_UNAVAILABLE"


@pytest.mark.asyncio
async def test_proxy_no_route_404():
    """Unrecognized path prefix returns 404."""
    from ohent_scheduler.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/unknown/resource", headers={"x-request-id": "req-404"})
        assert resp.status_code == 404
        body = resp.json()
        assert body["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_proxy_backend_error_passthrough():
    """Backend 4xx/5xx errors pass through as-is."""
    from ohent_scheduler.main import app

    mock_response = MagicMock()
    mock_response.status_code = 422
    mock_response.json.return_value = {"code": "VALIDATION_ERROR", "message": "bad input"}

    with patch("ohent_scheduler.proxy.httpx.AsyncClient") as mock_client_cls:
        mock_instance = AsyncMock()
        mock_instance.request = AsyncMock(return_value=mock_response)
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_cm

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                "/api/v1/market/plugins",
                headers={"x-request-id": "req-422"},
            )
            assert resp.status_code == 422
