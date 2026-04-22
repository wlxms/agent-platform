"""M1-auth-rbac smoke tests — run against LIVE Auth service on port 8001.

Requires: Auth service running at http://localhost:8001
Run: python -m pytest tests/test_smoke_m1_auth_rbac.py -v -m smoke
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

import pytest

pytestmark = pytest.mark.smoke

BASE = "http://localhost:8001/internal/auth"
ADMIN_KEY = "oh-admin-key-default"


def _req(method: str, path: str, token: str | None = None, body: dict | None = None) -> dict:
    """Make HTTP request, return parsed JSON."""
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"_status": e.code, "_error": json.loads(e.read())}


def _login() -> tuple[str, dict]:
    """Login with admin key, return (token, response_data)."""
    resp = _req("POST", "/login", body={"api_key": ADMIN_KEY})
    assert "data" in resp, f"Login failed: {resp}"
    token = resp["data"]["token"]
    return token, resp["data"]


# ============================================================
# T1.3: Permissions & Roles endpoints
# ============================================================


class TestPermissionsEndpoint:

    def test_get_permissions(self):
        resp = _req("GET", "/permissions")
        assert "data" in resp
        items = resp["data"]["items"]
        assert len(items) == 14, f"Expected 14 permissions, got {len(items)}"
        ids = {p["id"] for p in items}
        assert "agents:create" in ids
        assert "roles:manage" in ids

    def test_get_roles(self):
        resp = _req("GET", "/roles")
        assert "data" in resp
        items = resp["data"]["items"]
        assert len(items) == 3
        role_map = {r["name"]: r["permissions"] for r in items}
        assert role_map["admin"] == ["*"]
        assert len(role_map["manager"]) == 7
        assert "agents:create" in role_map["member"]


# ============================================================
# T1.0-T1.1: Member CRUD via API (through service + routes)
# ============================================================


class TestMemberCRUD:

    @pytest.fixture(scope="class")
    def token(self):
        t, _ = _login()
        return t

    def test_list_members_before(self, token):
        resp = _req("GET", "/org/org-root/members", token=token)
        # list_members uses list_response (items/total/page/page_size)
        assert "total" in resp
        assert resp["total"] >= 1
        assert len(resp["items"]) >= 1

    def test_add_member_invalid_role(self, token):
        """Adding with superadmin role should return VALIDATION_ERROR."""
        resp = _req("POST", "/org/org-root/members", token=token,
                     body={"user_id": "user-admin", "role": "superadmin"})
        # The user exists, but role is invalid
        assert resp.get("_status") == 422 or "VALIDATION_ERROR" in str(resp)

    def test_remove_nonexistent_member(self, token):
        resp = _req("DELETE", "/org/org-root/members/nonexistent-user-id", token=token)
        assert resp.get("_status") == 404 or "NOT_FOUND" in str(resp)

    def test_update_member_role_invalid(self, token):
        resp = _req("PUT", "/org/org-root/members/user-admin", token=token,
                     body={"role": "nonexistent"})
        assert resp.get("_status") == 422 or "VALIDATION_ERROR" in str(resp)

    def test_unauthorized_access(self):
        """Endpoints should require Bearer token."""
        resp = _req("POST", "/org/org-root/members", body={"user_id": "x", "role": "member"})
        assert resp.get("_status") == 401


# ============================================================
# T1.2: API Key Renew
# ============================================================


class TestApiKeyRenew:

    @pytest.fixture(scope="class")
    def auth(self):
        t, data = _login()
        return {"token": t, "data": data}

    def test_renew_nonexistent_key(self, auth):
        resp = _req("POST", "/org/org-root/api-keys/nonexistent-id/renew",
                     token=auth["token"], body={"expires_in_days": 30})
        assert resp.get("_status") == 404 or "NOT_FOUND" in str(resp)

    def test_renew_invalid_days(self, auth):
        resp = _req("POST", "/org/org-root/api-keys/any-id/renew",
                     token=auth["token"], body={"expires_in_days": 0})
        assert resp.get("_status") == 422 or "VALIDATION_ERROR" in str(resp)

    def test_renew_unauthorized(self):
        resp = _req("POST", "/org/org-root/api-keys/any-id/renew",
                     body={"expires_in_days": 30})
        assert resp.get("_status") == 401


# ============================================================
# Full chain: Login → Get Token → Test all new endpoints
# ============================================================


class TestFullChain:

    def test_complete_auth_flow(self):
        """Full auth flow: login → get me → permissions → roles → members list."""
        # 1. Login
        token, login_resp = _login()
        assert token
        # login wraps in data_response: resp["data"]["user"]["role"]
        user = login_resp["user"]
        assert user["role"] == "admin"
        assert user["org_id"] == "org-root"

        # 2. Get me
        resp = _req("GET", "/me", token=token)
        assert "data" in resp
        assert resp["data"]["role"] == "admin"

        # 3. Permissions
        resp = _req("GET", "/permissions", token=token)
        assert resp["data"]["total"] == 14

        # 4. Roles
        resp = _req("GET", "/roles", token=token)
        assert resp["data"]["total"] == 3

        # 5. Members list (uses list_response, not data_response)
        resp = _req("GET", "/org/org-root/members", token=token)
        assert resp["total"] >= 1

        # 6. Org tree
        resp = _req("GET", "/org/tree", token=token)
        assert "data" in resp
        assert "children" in resp["data"]

        # 7. API keys list (uses list_response)
        resp = _req("GET", "/api-keys", token=token)
        assert "total" in resp
