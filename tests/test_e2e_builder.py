"""E2E test — builder config flow (T9.3).

Covers: validate → create → get → update → export → delete via Gateway (port 8000).
Requires all services running (dev_start.ps1).

Run:
  pytest tests/test_e2e_builder.py -v
  pytest tests/test_e2e_builder.py -v -m e2e
"""
from __future__ import annotations

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


class TestBuilderConfigFlow:
    """T9.3 — Builder config flow E2E."""

    @pytest.mark.e2e
    def test_builder_config_flow(self, auth_headers):
        suffix = uuid.uuid4().hex[:8]

        # 1. Validate config
        resp = httpx.post(
            f"{GATEWAY_URL}/api/v1/market/configs/validate",
            json={"personality": {"system_prompt": "Hi"}, "model": {"provider": "litellm"}},
            headers=auth_headers,
            timeout=10,
        )
        assert resp.status_code == 200, f"Validate failed: {resp.text}"
        validation = resp.json()["data"]
        assert validation["valid"] is True, f"Config should be valid, got: {validation}"

        # 2. Create config
        config_name = f"e2e-config-{suffix}"
        resp = httpx.post(
            f"{GATEWAY_URL}/api/v1/market/configs",
            json={
                "name": config_name,
                "author_id": "u-e2e-builder",
                "org_id": "org-root",
                "model": {"provider": "litellm"},
            },
            headers=auth_headers,
            timeout=10,
        )
        assert resp.status_code in (200, 201), f"Create config failed: {resp.text}"
        config = resp.json()["data"]
        config_id = config["id"]
        assert config_id is not None, "Config ID missing from create response"

        # 3. Get config
        resp = httpx.get(
            f"{GATEWAY_URL}/api/v1/market/configs/{config_id}",
            headers=auth_headers,
            timeout=10,
        )
        assert resp.status_code == 200, f"Get config failed: {resp.text}"

        # 4. Update config
        resp = httpx.put(
            f"{GATEWAY_URL}/api/v1/market/configs/{config_id}",
            json={"name": f"updated-{config_name}"},
            headers=auth_headers,
            timeout=10,
        )
        assert resp.status_code == 200, f"Update config failed: {resp.text}"

        # 5. Export config
        resp = httpx.get(
            f"{GATEWAY_URL}/api/v1/market/configs/{config_id}/export",
            params={"format": "json"},
            headers=auth_headers,
            timeout=10,
        )
        assert resp.status_code == 200, f"Export config failed: {resp.text}"

        # 6. Delete config
        resp = httpx.delete(
            f"{GATEWAY_URL}/api/v1/market/configs/{config_id}",
            headers=auth_headers,
            timeout=10,
        )
        assert resp.status_code == 200, f"Delete config failed: {resp.text}"
