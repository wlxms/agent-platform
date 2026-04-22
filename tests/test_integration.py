r"""
Cross-service integration tests: Market, Billing, Memory, Error handling, Request-ID tracing.

Prerequisites:
  1. Run: .\scripts\dev_start.ps1
  2. Run: python -m pytest tests/test_integration.py -v -m integration
"""
import time

import httpx
import pytest

GATEWAY_URL = "http://localhost:8000"
API_KEY = "oh-admin-key-default"


def services_available() -> bool:
    """Check if gateway is reachable."""
    try:
        resp = httpx.get(f"{GATEWAY_URL}/health", timeout=3)
        return resp.status_code == 200
    except Exception:
        return False


@pytest.fixture(scope="session")
def ensure_services():
    """Skip tests if services are not running."""
    if not services_available():
        pytest.skip(r"Services not running. Start with: .\scripts\dev_start.ps1")


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


class TestMarketGatewayAccess:
    """Verify market templates are accessible through gateway."""

    @pytest.mark.integration
    def test_market_templates_returns_items(self, ensure_services, auth_headers):
        """Login -> GET /api/v1/market/templates -> verify items array returned."""
        resp = httpx.get(
            f"{GATEWAY_URL}/api/v1/market/templates",
            headers=auth_headers,
            timeout=10,
        )
        assert resp.status_code == 200, f"Market templates failed: {resp.text}"
        data = resp.json()
        assert "items" in data
        assert isinstance(data["items"], list)
        assert len(data["items"]) >= 1


class TestBillingGatewayAccess:
    """Verify billing usage summary is accessible through gateway."""

    @pytest.mark.integration
    def test_billing_usage_summary_has_total_cost(self, ensure_services, auth_headers):
        """Login -> GET /api/v1/billing/usage/summary -> verify data with total_cost."""
        resp = httpx.get(
            f"{GATEWAY_URL}/api/v1/billing/usage/summary",
            headers=auth_headers,
            timeout=10,
        )
        assert resp.status_code == 200, f"Billing summary failed: {resp.text}"
        data = resp.json()["data"]
        assert "total_cost" in data


class TestMemoryGatewayAccess:
    """Verify memory assets CRUD is accessible through gateway."""

    @pytest.mark.integration
    def test_memory_assets_list_and_create(self, ensure_services, auth_headers):
        """Login -> GET assets (verify items) -> POST create (verify success)."""
        # List assets
        resp = httpx.get(
            f"{GATEWAY_URL}/api/v1/memory/assets",
            headers=auth_headers,
            timeout=10,
        )
        assert resp.status_code == 200, f"Memory list failed: {resp.text}"
        data = resp.json()
        assert "items" in data
        assert isinstance(data["items"], list)

        # Create asset
        unique_path = f"integration-test/{int(time.time())}.txt"
        resp = httpx.post(
            f"{GATEWAY_URL}/api/v1/memory/assets",
            json={
                "path": unique_path,
                "content": "integration test content",
                "content_type": "text/plain",
            },
            headers=auth_headers,
            timeout=10,
        )
        assert resp.status_code == 200, f"Memory create failed: {resp.text}"
        created = resp.json()["data"]
        assert created["path"] == unique_path


class TestErrorNotFound:
    """Verify 404 handling through gateway."""

    @pytest.mark.integration
    def test_get_nonexistent_agent_returns_404(self, ensure_services, auth_headers):
        """Login -> GET /api/v1/agents/nonexistent-id -> verify 404 with NOT_FOUND."""
        resp = httpx.get(
            f"{GATEWAY_URL}/api/v1/agents/nonexistent-id",
            headers=auth_headers,
            timeout=10,
        )
        assert resp.status_code == 404
        body = resp.json()
        assert body["detail"]["code"] == "NOT_FOUND"


class TestRequestIdTrace:
    """Verify X-Request-ID header is present in responses."""

    @pytest.mark.integration
    def test_auth_me_has_request_id_header(self, ensure_services, auth_headers):
        """Login -> GET /api/v1/auth/me -> verify X-Request-ID in response headers."""
        resp = httpx.get(
            f"{GATEWAY_URL}/api/v1/auth/me",
            headers=auth_headers,
            timeout=10,
        )
        assert resp.status_code == 200
        request_id = resp.headers.get("x-request-id")
        assert request_id is not None
        assert len(request_id.strip()) > 0
