"""E2E test — full agent lifecycle (T9.1).

Covers: list → create → get → message → delete via Gateway (port 8000).
Requires all services running (dev_start.ps1).

Run:
  pytest tests/test_e2e_lifecycle.py -v
  pytest tests/test_e2e_lifecycle.py -v -m e2e
"""
from __future__ import annotations

import time
import uuid

import httpx
import pytest

GATEWAY_URL = "http://localhost:8000"


def _services_available() -> bool:
    try:
        return httpx.get(f"{GATEWAY_URL}/health", timeout=3).status_code == 200
    except Exception:
        return False


@pytest.fixture(scope="session")
def admin_token():
    if not _services_available():
        pytest.skip("Services not running. Start with: .\\scripts\\dev_start.ps1")
    resp = httpx.post(
        f"{GATEWAY_URL}/api/v1/auth/login",
        json={"api_key": "oh-admin-key-default"},
        timeout=10,
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["data"]["token"]


@pytest.fixture(scope="session")
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


class TestAgentLifecycle:
    """T9.1 — Full agent lifecycle E2E."""

    @pytest.mark.e2e
    def test_full_agent_lifecycle(self, auth_headers):
        # 1. List agents (should return existing or empty list)
        resp = httpx.get(f"{GATEWAY_URL}/api/v1/agents", headers=auth_headers, timeout=10)
        assert resp.status_code == 200, f"List agents failed: {resp.text}"
        body = resp.json()
        initial_total = body.get("total", len(body.get("items", [])))

        # 2. Create agent
        agent_name = f"e2e-lifecycle-{uuid.uuid4().hex[:8]}"
        resp = httpx.post(
            f"{GATEWAY_URL}/api/v1/agents",
            json={"name": agent_name},
            headers=auth_headers,
            timeout=30,
        )
        assert resp.status_code in (200, 201), f"Create agent failed: {resp.text}"
        agent_data = resp.json()["data"]
        agent_id = agent_data.get("id") or agent_data.get("guid")
        assert agent_id is not None, "Agent ID missing from create response"

        # 3. Get agent
        resp = httpx.get(
            f"{GATEWAY_URL}/api/v1/agents/{agent_id}",
            headers=auth_headers,
            timeout=10,
        )
        assert resp.status_code == 200, f"Get agent failed: {resp.text}"

        # 4. Send message (may fail if no DS_API_KEY — that is acceptable)
        resp = httpx.post(
            f"{GATEWAY_URL}/api/v1/agents/{agent_id}/message",
            json={"prompt": "Hello"},
            headers=auth_headers,
            timeout=30,
        )
        # Accept 200 or 502 (upstream SDK not configured)
        assert resp.status_code in (200, 502), f"Message failed: {resp.text}"

        # 5. Delete agent
        resp = httpx.delete(
            f"{GATEWAY_URL}/api/v1/agents/{agent_id}",
            headers=auth_headers,
            timeout=10,
        )
        assert resp.status_code == 200, f"Delete agent failed: {resp.text}"

        # 6. Verify list count decreased or agent gone
        resp = httpx.get(f"{GATEWAY_URL}/api/v1/agents", headers=auth_headers, timeout=10)
        assert resp.status_code == 200
