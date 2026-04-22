"""Tests for org member CRUD — add, remove, update role."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from agentp_shared.config import db_settings
from agentp_auth import service
from agentp_shared import redis as shared_redis
from agentp_shared.models import User, Organization

_test_engine = create_async_engine(db_settings.url, echo=False, poolclass=NullPool)
_test_session_factory = async_sessionmaker(_test_engine, class_=AsyncSession, expire_on_commit=False)


def _uniq() -> str:
    return uuid.uuid4().hex[:8]


@pytest.fixture
async def db():
    shared_redis.redis_client = None
    async with _test_session_factory() as session:
        await service.seed_default_data(session)
        yield session
        await session.rollback()
        from sqlalchemy import delete
        seed_ids = {"user-admin", "user-demo"}
        await session.execute(
            delete(User).where(
                User.org_id == "org-root",
                User.id.notin_(seed_ids),
            )
        )
        await session.commit()


class TestAddMember:

    async def test_add_member_to_org(self, db):
        tag = _uniq()
        org = Organization(name=f"Test Org {tag}")
        db.add(org)
        await db.commit()
        user = User(org_id=org.id, username=f"newuser-{tag}", email=f"nu-{tag}@test.com", role="member")
        db.add(user)
        await db.commit()
        member = await service.add_org_member(db, org_id=org.id, user_id=user.id, role="member")
        assert member["org_id"] == org.id
        assert member["user_id"] == user.id
        assert member["role"] == "member"

    async def test_add_member_invalid_role(self, db):
        tag = _uniq()
        org = Organization(name=f"Test Org Inv {tag}")
        db.add(org)
        await db.commit()
        user = User(org_id=org.id, username=f"badrole-{tag}", email=f"br-{tag}@test.com", role="member")
        db.add(user)
        await db.commit()
        with pytest.raises(service.AuthError) as exc_info:
            await service.add_org_member(db, org_id=org.id, user_id=user.id, role="superadmin")
        assert exc_info.value.code == "VALIDATION_ERROR"


class TestRemoveMember:

    async def test_remove_member_from_org(self, db):
        tag = _uniq()
        org = Organization(name=f"Test Org Rem {tag}")
        db.add(org)
        await db.commit()
        user = User(org_id=org.id, username=f"remuser-{tag}", email=f"ru-{tag}@test.com", role="member", status="active")
        db.add(user)
        await db.commit()
        await service.remove_org_member(db, org_id=org.id, user_id=user.id)
        await db.refresh(user)
        assert user.status == "removed"

    async def test_remove_nonexistent_member(self, db):
        with pytest.raises(service.AuthError) as exc_info:
            await service.remove_org_member(db, org_id="org-root", user_id="nonexistent-id")
        assert exc_info.value.code == "NOT_FOUND"


class TestUpdateMemberRole:

    async def test_update_member_role(self, db):
        tag = _uniq()
        org = Organization(name=f"Test Org Upd {tag}")
        db.add(org)
        await db.commit()
        user = User(org_id=org.id, username=f"uprole-{tag}", email=f"ur-{tag}@test.com", role="member", status="active")
        db.add(user)
        await db.commit()
        result = await service.update_member_role(db, org_id=org.id, user_id=user.id, role="manager")
        assert result["role"] == "manager"

    async def test_update_member_invalid_role(self, db):
        tag = _uniq()
        org = Organization(name=f"Test Org BadUp {tag}")
        db.add(org)
        await db.commit()
        user = User(org_id=org.id, username=f"badup-{tag}", email=f"bu-{tag}@test.com", role="member", status="active")
        db.add(user)
        await db.commit()
        with pytest.raises(service.AuthError) as exc_info:
            await service.update_member_role(db, org_id=org.id, user_id=user.id, role="nonexistent")
        assert exc_info.value.code == "VALIDATION_ERROR"
