"""Gateway middleware tests: JWT auth, request_id injection, request forwarding."""
import pytest
import jwt
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import timedelta, timezone, datetime


def _make_token(**overrides):
    from agentp_shared.security import create_access_token
    data = {"sub": "user-1", "org_id": "org-001", "role": "user", "permissions": ["read"]}
    data.update(overrides)
    return create_access_token(data)


def _has_request_id(headers):
    return any(h.lower() == "x-request-id" for h in headers.keys())


@pytest.mark.asyncio
async def test_health_no_auth():
    from agentp_gateway.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        assert _has_request_id(resp.headers)


@pytest.mark.asyncio
async def test_login_no_auth_required():
    from agentp_gateway.main import app
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": {"token": "test"}}

    with patch("agentp_gateway.middleware.httpx.AsyncClient") as mock_client:
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=AsyncMock(
            request=AsyncMock(return_value=mock_response)
        ))
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value = mock_cm

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/api/v1/auth/login", json={"api_key": "test"})
            assert _has_request_id(resp.headers)


@pytest.mark.asyncio
async def test_protected_route_no_token():
    from agentp_gateway.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/agents")
        assert resp.status_code == 401
        assert resp.json()["code"] == "UNAUTHORIZED"
        assert _has_request_id(resp.headers)


@pytest.mark.asyncio
async def test_protected_route_valid_token():
    from agentp_gateway.main import app
    token = _make_token()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"items": [], "total": 0, "page": 1, "page_size": 20}

    with patch("agentp_gateway.middleware.httpx.AsyncClient") as mock_client:
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=AsyncMock(
            request=AsyncMock(return_value=mock_response)
        ))
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value = mock_cm

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                "/api/v1/agents",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            assert _has_request_id(resp.headers)


@pytest.mark.asyncio
async def test_expired_token():
    from agentp_gateway.main import app
    from agentp_shared.security import create_access_token
    token = create_access_token({"sub": "u1"}, expires_delta=timedelta(seconds=-1))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/agents",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401
        assert resp.json()["details"].get("expired") is True


@pytest.mark.asyncio
async def test_invalid_token():
    from agentp_gateway.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/agents",
            headers={"Authorization": "Bearer garbage.token.here"},
        )
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_upstream_unavailable():
    from agentp_gateway.main import app
    token = _make_token()

    with patch("agentp_gateway.middleware.httpx.AsyncClient") as mock_client:
        mock_cm = AsyncMock()
        mock_instance = AsyncMock()
        mock_instance.request.side_effect = Exception("Scheduler not running")
        mock_cm.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_client.return_value = mock_cm

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                "/api/v1/agents",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 502
            assert resp.json()["code"] == "UPSTREAM_UNAVAILABLE"
