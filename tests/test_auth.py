"""Auth service API tests - internal endpoints."""
import pytest
from httpx import AsyncClient, ASGITransport


@pytest.fixture(autouse=True)
def setup_auth():
    from ohent_auth.service import init_api_keys
    init_api_keys()


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_login_success():
    from ohent_auth.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/internal/auth/login", json={"api_key": "oh-admin-key"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "token" in data
        assert "refresh_token" in data
        assert "expires_at" in data
        assert data["user"]["role"] == "admin"
        assert data["user"]["id"] == "user-admin"


@pytest.mark.asyncio
async def test_login_invalid_key():
    from ohent_auth.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/internal/auth/login", json={"api_key": "invalid-key"})
        assert resp.status_code == 401
        assert resp.json()["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_refresh_success():
    from ohent_auth.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        login_resp = await client.post("/internal/auth/login", json={"api_key": "oh-user-key"})
        refresh_token = login_resp.json()["data"]["refresh_token"]

        resp = await client.post("/internal/auth/refresh", json={"refresh_token": refresh_token})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "token" in data
        assert "expires_at" in data


@pytest.mark.asyncio
async def test_refresh_invalid_token():
    from ohent_auth.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/internal/auth/refresh", json={"refresh_token": "invalid"})
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_success():
    from ohent_auth.main import app
    from ohent_auth.service import login
    token_info = login("oh-admin-key")
    token = token_info["token"]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/internal/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["role"] == "admin"


@pytest.mark.asyncio
async def test_me_no_token():
    from ohent_auth.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/internal/auth/me")
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_logout():
    from ohent_auth.main import app
    from ohent_auth.service import login
    token_info = login("oh-admin-key")
    token = token_info["token"]

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/internal/auth/logout", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["ok"] is True


@pytest.mark.asyncio
async def test_login_custom_api_key():
    """init_api_keys with custom keys should work."""
    from ohent_auth.service import init_api_keys, login
    init_api_keys({"my-custom-key": {
        "id": "user-custom",
        "name": "Custom",
        "role": "admin",
        "org_id": "org-custom",
        "permissions": ["agent:manage"],
    }})
    result = login("my-custom-key")
    assert result["user"]["id"] == "user-custom"
    assert result["user"]["org_id"] == "org-custom"
    assert "agent:manage" in result["user"]["permissions"]
    # Restore defaults
    init_api_keys()


@pytest.mark.asyncio
async def test_login_returns_token_fields():
    """Login response must contain token, refresh_token, expires_at, user."""
    from ohent_auth.service import login
    result = login("oh-user-key")
    assert "token" in result
    assert "refresh_token" in result
    assert "expires_at" in result
    assert "user" in result
    assert result["user"]["role"] == "user"
    assert result["user"]["org_id"] == "org-001"


@pytest.mark.asyncio
async def test_refresh_with_access_token_fails():
    """Using an access token as refresh token should fail."""
    from ohent_auth.service import login
    access = login("oh-user-key")["token"]
    from ohent_auth.service import refresh
    try:
        refresh(access)
        assert False, "Should have raised"
    except Exception as e:
        assert e.code == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_get_user_info_structure():
    """get_user_info should return expected fields from token payload."""
    from ohent_auth.service import get_user_info
    payload = {
        "sub": "user-admin",
        "org_id": "root",
        "role": "admin",
        "permissions": ["*"],
    }
    info = get_user_info(payload)
    assert info["id"] == "user-admin"
    assert info["org_id"] == "root"
    assert info["role"] == "admin"
    assert info["permissions"] == ["*"]


@pytest.mark.asyncio
async def test_schemas_validation():
    """LoginRequest and RefreshRequest schema validation."""
    from ohent_auth.schemas import LoginRequest, RefreshRequest
    # Valid login
    req = LoginRequest(api_key="test-key")
    assert req.api_key == "test-key"
    # Valid refresh
    req2 = RefreshRequest(refresh_token="jwt-token")
    assert req2.refresh_token == "jwt-token"
    # Missing fields
    try:
        LoginRequest()
        assert False, "Should raise validation error"
    except Exception:
        pass
