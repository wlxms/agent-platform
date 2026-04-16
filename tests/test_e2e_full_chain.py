r"""
Full chain E2E test: Gateway -> Scheduler -> Auth/Host -> SDK

Prerequisites:
  1. Run: podman start agentp-pg agentp-redis
  2. Run: .\scripts\dev_start.ps1
  3. Run: python -m pytest tests/test_e2e_full_chain.py -v -m e2e
"""
import time

import httpx
import pytest

GATEWAY_URL = "http://localhost:8000"
API_KEY = "oh-admin-key"


def services_available() -> bool:
    """Check if all required services are running."""
    try:
        resp = httpx.get(f"{GATEWAY_URL}/health", timeout=3)
        return resp.status_code == 200
    except Exception:
        return False


@pytest.fixture(scope="session")
def ensure_services():
    """Skip tests if services are not running."""
    if not services_available():
        pytest.skip(
            r"Services not running. Start with: .\scripts\dev_start.ps1"
        )


@pytest.fixture(scope="session")
def admin_token(ensure_services):
    """Get JWT token via API Key login."""
    resp = httpx.post(
        f"{GATEWAY_URL}/api/v1/auth/login",
        json={"api_key": API_KEY},
        timeout=10,
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["data"]["token"]


@pytest.fixture(scope="session")
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


class TestFullChain:
    """E2E test: login -> agents CRUD -> verify"""

    @pytest.mark.e2e
    def test_01_login(self, ensure_services):
        """Step 1: Login with API Key, get JWT."""
        resp = httpx.post(
            f"{GATEWAY_URL}/api/v1/auth/login",
            json={"api_key": API_KEY},
            timeout=10,
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "token" in data
        assert "refresh_token" in data
        assert "expires_at" in data
        assert data["user"]["role"] == "admin"
        assert data["user"]["org_id"] == "root"
        assert "x-request-id" in resp.headers

    @pytest.mark.e2e
    def test_02_me(self, ensure_services, auth_headers):
        """Step 2: Get current user info."""
        resp = httpx.get(
            f"{GATEWAY_URL}/api/v1/auth/me",
            headers=auth_headers,
            timeout=10,
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["role"] == "admin"

    @pytest.mark.e2e
    def test_03_agents_list_empty(self, ensure_services, auth_headers):
        """Step 3: List agents (should be empty or contain previous test data)."""
        resp = httpx.get(
            f"{GATEWAY_URL}/api/v1/agents",
            headers=auth_headers,
            timeout=10,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data

    @pytest.mark.e2e
    def test_04_create_agent(self, ensure_services, auth_headers):
        """Step 4: Create a new agent instance."""
        resp = httpx.post(
            f"{GATEWAY_URL}/api/v1/agents",
            json={"name": f"e2e-test-{int(time.time())}"},
            headers=auth_headers,
            timeout=30,
        )
        assert resp.status_code == 200, f"Create failed: {resp.text}"
        data = resp.json()["data"]
        assert data["name"].startswith("e2e-test")
        assert data["status"] in ("ready", "running", "seeding")
        assert data["id"]

    @pytest.mark.e2e
    def test_05_no_auth_returns_401(self, ensure_services):
        """Step 5: Request without JWT returns 401."""
        resp = httpx.get(f"{GATEWAY_URL}/api/v1/agents", timeout=10)
        assert resp.status_code == 401
        assert resp.json()["code"] == "UNAUTHORIZED"

    @pytest.mark.e2e
    def test_06_invalid_token_returns_401(self, ensure_services):
        """Step 6: Invalid token returns 401."""
        resp = httpx.get(
            f"{GATEWAY_URL}/api/v1/agents",
            headers={"Authorization": "Bearer invalid.token.here"},
            timeout=10,
        )
        assert resp.status_code == 401

    @pytest.mark.e2e
    def test_07_request_id_unique(self, ensure_services, auth_headers):
        """Step 7: Each request has a unique request_id."""
        request_ids: set[str] = set()
        for _ in range(3):
            resp = httpx.get(
                f"{GATEWAY_URL}/api/v1/agents",
                headers=auth_headers,
                timeout=10,
            )
            rid = resp.headers.get("x-request-id", "")
            request_ids.add(rid)
        assert len(request_ids) == 3, "request_id should be unique per request"

    @pytest.mark.e2e
    def test_08_error_response_format(self, ensure_services):
        """Step 8: Error responses match api-protocol.md format."""
        resp = httpx.get(f"{GATEWAY_URL}/api/v1/agents", timeout=10)
        body = resp.json()
        assert "code" in body
        assert "message" in body
        assert "request_id" in body
        assert isinstance(body.get("details"), dict)

    @pytest.mark.e2e
    @pytest.mark.skipif(
        not __import__("os").environ.get("DS_API_KEY"),
        reason="DS_API_KEY not set (required for send_message E2E)",
    )
    def test_09_send_message(self, ensure_services, auth_headers):
        """Step 9: Create agent then send a message through the full chain."""
        # Create agent
        resp = httpx.post(
            f"{GATEWAY_URL}/api/v1/agents",
            json={"name": f"msg-e2e-{int(time.time())}"},
            headers=auth_headers,
            timeout=30,
        )
        assert resp.status_code == 200, f"Create failed: {resp.text}"
        agent_id = resp.json()["data"]["id"]

        # Send message through gateway -> scheduler -> host -> SDK
        resp = httpx.post(
            f"{GATEWAY_URL}/api/v1/agents/{agent_id}/message",
            json={"prompt": "hello from e2e", "model": "gpt-4"},
            headers=auth_headers,
            timeout=30,
        )
        assert resp.status_code == 200, f"Send message failed: {resp.text}"
        data = resp.json()["data"]
        assert data["instance_id"] == agent_id
        assert "reply_text" in data

    @pytest.mark.e2e
    def test_10_destroy_agent(self, ensure_services, auth_headers):
        """Step 10: Create then destroy an agent through full chain."""
        resp = httpx.post(
            f"{GATEWAY_URL}/api/v1/agents",
            json={"name": f"destroy-e2e-{int(time.time())}"},
            headers=auth_headers,
            timeout=30,
        )
        assert resp.status_code == 200, f"Create failed: {resp.text}"
        agent_id = resp.json()["data"]["id"]

        resp = httpx.delete(
            f"{GATEWAY_URL}/api/v1/agents/{agent_id}",
            headers=auth_headers,
            timeout=30,
        )
        assert resp.status_code == 200, f"Destroy failed: {resp.text}"
        assert resp.json()["ok"] is True
