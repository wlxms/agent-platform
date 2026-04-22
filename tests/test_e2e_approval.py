"""E2E test — approval workflow (T9.2).

Covers: create → list → approve → history via Gateway (port 8000).
Requires all services running (dev_start.ps1).

Run:
  pytest tests/test_e2e_approval.py -v
  pytest tests/test_e2e_approval.py -v -m e2e
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


class TestApprovalWorkflow:
    """T9.2 — Approval workflow E2E."""

    @pytest.mark.e2e
    def test_approval_workflow(self, auth_headers):
        suffix = uuid.uuid4().hex[:8]

        # 1. Create approval request
        resp = httpx.post(
            f"{GATEWAY_URL}/api/v1/approvals",
            json={
                "org_id": "org-root",
                "applicant_id": f"u-e2e-{suffix}",
                "template_name": f"E2E-Test-{suffix}",
                "reason": "M9 E2E approval test",
            },
            headers=auth_headers,
            timeout=10,
        )
        assert resp.status_code in (200, 201), f"Create approval failed: {resp.text}"
        body = resp.json()
        approval = body.get("data", body)
        approval_id = approval["id"]
        assert approval["status"] == "pending", f"Expected pending, got {approval['status']}"

        # 2. List pending approvals
        resp = httpx.get(
            f"{GATEWAY_URL}/api/v1/approvals",
            params={"org_id": "org-root", "status": "pending"},
            headers=auth_headers,
            timeout=10,
        )
        assert resp.status_code == 200, f"List approvals failed: {resp.text}"
        list_body = resp.json()
        items = list_body.get("items", list_body.get("data", []))
        assert len(items) >= 1, "Should have at least one pending approval"

        # 3. Approve
        resp = httpx.post(
            f"{GATEWAY_URL}/api/v1/approvals/{approval_id}/approve",
            json={"reviewer_id": "admin-e2e"},
            headers=auth_headers,
            timeout=10,
        )
        assert resp.status_code == 200, f"Approve failed: {resp.text}"

        # 4. Check history
        resp = httpx.get(
            f"{GATEWAY_URL}/api/v1/approvals/history",
            params={"org_id": "org-root"},
            headers=auth_headers,
            timeout=10,
        )
        assert resp.status_code == 200, f"History failed: {resp.text}"
