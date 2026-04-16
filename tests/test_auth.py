"""Tests for auth service — runs against REAL PostgreSQL + Redis.

Requires: PostgreSQL + Redis running, alembic upgrade head applied.
Run: pytest tests/test_auth.py -v
"""
from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from agentp_shared.config import db_settings
from agentp_shared.security import decode_token
from agentp_auth import service
from agentp_shared import redis as shared_redis

# Test engine with NullPool — no connection reuse across loops
_test_engine = create_async_engine(db_settings.url, echo=False, poolclass=NullPool)
_test_session_factory = async_sessionmaker(_test_engine, class_=AsyncSession, expire_on_commit=False)


# ---- Fixtures ----

@pytest.fixture
async def db():
    """Provide a fresh DB session per test. Seeds DB and resets Redis connection."""
    # Reset Redis connection so it binds to current event loop
    shared_redis.redis_client = None
    async with _test_session_factory() as session:
        await service.seed_default_data(session)
        yield session


@pytest.fixture
def admin_key():
    return "oh-admin-key-default"


@pytest.fixture
def demo_key():
    return "oh-demo-key-default"


# ---- API Key Authentication ----

class TestAuthenticateApiKey:

    async def test_admin_key_authenticates(self, db, admin_key):
        result = await service.authenticate_api_key(admin_key, db)
        assert result is not None
        assert result["id"] == "user-admin"
        assert result["role"] == "admin"
        assert result["org_id"] == "org-root"

    async def test_demo_key_authenticates(self, db, demo_key):
        result = await service.authenticate_api_key(demo_key, db)
        assert result is not None
        assert result["id"] == "user-demo"
        assert result["role"] == "member"

    async def test_invalid_key_returns_none(self, db):
        result = await service.authenticate_api_key("oh-invalid-key", db)
        assert result is None

    async def test_empty_key_returns_none(self, db):
        result = await service.authenticate_api_key("", db)
        assert result is None

    async def test_auth_returns_api_key_id(self, db, admin_key):
        result = await service.authenticate_api_key(admin_key, db)
        assert "api_key_id" in result


# ---- Login ----

class TestLogin:

    async def test_login_success(self, db, admin_key):
        result = await service.login(admin_key, db)
        assert "token" in result
        assert "refresh_token" in result
        assert "expires_at" in result
        assert "user" in result
        assert result["user"]["role"] == "admin"

    async def test_login_returns_jwt_with_correct_fields(self, db, admin_key):
        result = await service.login(admin_key, db)
        payload = decode_token(result["token"])
        assert payload["sub"] == "user-admin"
        assert payload["org_id"] == "org-root"
        assert payload["role"] == "admin"
        assert payload["type"] == "access"
        assert "jti" in payload

    async def test_login_invalid_key_raises_auth_error(self, db):
        with pytest.raises(service.AuthError) as exc_info:
            await service.login("oh-bad-key", db)
        assert exc_info.value.code == "UNAUTHORIZED"

    async def test_login_demo_user(self, db, demo_key):
        result = await service.login(demo_key, db)
        assert result["user"]["role"] == "member"
        assert result["user"]["org_id"] == "org-demo"


# ---- Refresh ----

class TestRefresh:

    async def test_refresh_success(self, db, admin_key):
        login_result = await service.login(admin_key, db)
        refresh_result = await service.refresh(login_result["refresh_token"], db)
        assert "token" in refresh_result
        assert "expires_at" in refresh_result

    async def test_refresh_invalid_token_raises_error(self, db):
        with pytest.raises(service.AuthError) as exc_info:
            await service.refresh("invalid.token.here", db)
        assert exc_info.value.code == "UNAUTHORIZED"

    async def test_refresh_access_token_fails(self, db, admin_key):
        login_result = await service.login(admin_key, db)
        with pytest.raises(service.AuthError) as exc_info:
            await service.refresh(login_result["token"], db)
        assert exc_info.value.code == "UNAUTHORIZED"

    async def test_refresh_returns_new_token(self, db, admin_key):
        login_result = await service.login(admin_key, db)
        refresh_result = await service.refresh(login_result["refresh_token"], db)
        assert refresh_result["token"] != login_result["token"]


# ---- Logout ----

class TestLogout:

    async def test_logout_revokes_refresh_token(self, db, admin_key):
        login_result = await service.login(admin_key, db)
        await service.logout(refresh_token_str=login_result["refresh_token"])
        with pytest.raises(service.AuthError) as exc_info:
            await service.refresh(login_result["refresh_token"], db)
        assert "revoked" in exc_info.value.message

    async def test_logout_with_access_token_blacklists(self, db, admin_key):
        login_result = await service.login(admin_key, db)
        payload = decode_token(login_result["token"])
        jti = payload["jti"]
        await service.logout(access_token_jti=jti)
        assert await service.is_token_blacklisted(jti)

    async def test_logout_no_token_still_works(self):
        await service.logout()


# ---- Get User Info ----

class TestGetUserInfo:

    async def test_get_user_info_from_token(self, db, admin_key):
        login_result = await service.login(admin_key, db)
        payload = decode_token(login_result["token"])
        user_info = await service.get_user_info(payload, db)
        assert user_info["id"] == "user-admin"
        assert user_info["role"] == "admin"

    async def test_get_user_info_no_user(self, db):
        payload = {"sub": "nonexistent-user", "role": "guest", "org_id": "", "permissions": []}
        user_info = await service.get_user_info(payload, db)
        assert user_info["name"] == ""


# ---- API Key Management ----

class TestApiKeyManagement:

    async def test_create_api_key(self, db):
        result = await service.create_api_key(db, org_id="org-root", user_id="user-admin", name="Test Key")
        assert "api_key" in result
        assert "id" in result
        assert result["name"] == "Test Key"
        assert result["key_prefix"] == result["api_key"][:8]
        raw_key = result["api_key"]
        auth_result = await service.authenticate_api_key(raw_key, db)
        assert auth_result is not None
        assert auth_result["api_key_id"] == result["id"]

    async def test_create_api_key_with_expiry(self, db):
        from datetime import datetime, timezone, timedelta
        result = await service.create_api_key(db, org_id="org-root", user_id="user-admin", name="Expiring Key", expires_in_days=30)
        assert result["expires_at"] is not None
        expires_at = datetime.fromisoformat(result["expires_at"])
        now = datetime.now(timezone.utc)
        assert expires_at > now
        assert expires_at < now + timedelta(days=31)

    async def test_list_api_keys(self, db):
        result = await service.list_api_keys(db, org_id="org-root")
        assert "items" in result
        assert "total" in result
        assert result["total"] >= 1

    async def test_revoke_api_key(self, db):
        created = await service.create_api_key(db, org_id="org-root", user_id="user-admin", name="Revoke Me")
        await service.revoke_api_key(db, org_id="org-root", key_id=created["id"])
        auth_result = await service.authenticate_api_key(created["api_key"], db)
        assert auth_result is None

    async def test_revoke_nonexistent_key_raises_error(self, db):
        with pytest.raises(service.AuthError) as exc_info:
            await service.revoke_api_key(db, org_id="org-root", key_id="nonexistent-id")
        assert exc_info.value.code == "NOT_FOUND"


# ---- Organization Management ----

class TestOrgManagement:

    async def test_get_root_org(self, db):
        org = await service.get_organization(db, "org-root")
        assert org is not None
        assert org["name"] == "Root"
        assert org["plan"] == "enterprise"

    async def test_get_nonexistent_org(self, db):
        org = await service.get_organization(db, "nonexistent")
        assert org is None

    async def test_create_sub_org(self, db):
        result = await service.create_organization(db, name="SubOrg", parent_id="org-root", plan="basic")
        assert result["name"] == "SubOrg"
        assert result["parent_id"] == "org-root"

    async def test_get_org_tree(self, db):
        tree = await service.get_org_tree(db, depth=3)
        assert "children" in tree
        assert len(tree["children"]) >= 1

    async def test_get_org_tree_by_id(self, db):
        tree = await service.get_org_tree(db, org_id="org-root", depth=2)
        assert tree["name"] == "Root"


# ---- User Management ----

class TestUserManagement:

    async def test_create_user(self, db):
        import uuid
        uname = f"testuser-{uuid.uuid4().hex[:8]}"
        result = await service.create_user(db, org_id="org-root", username=uname, email=f"{uname}@localhost", role="member")
        assert result["username"] == uname
        assert result["org_id"] == "org-root"

    async def test_list_org_members(self, db):
        result = await service.list_org_members(db, org_id="org-root")
        assert result["total"] >= 1
        assert any(m["username"] == "admin" for m in result["items"])


# ---- Schema Validation ----

class TestSchemaValidation:

    async def test_login_response_schema(self, db, admin_key):
        result = await service.login(admin_key, db)
        assert all(k in result for k in ["token", "refresh_token", "expires_at", "user"])

    async def test_user_info_structure(self, db, admin_key):
        result = await service.login(admin_key, db)
        payload = decode_token(result["token"])
        user_info = await service.get_user_info(payload, db)
        assert "id" in user_info
        assert "role" in user_info
        assert "org_id" in user_info
        assert "permissions" in user_info
