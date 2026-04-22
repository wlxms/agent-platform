"""Tests for API key renewal endpoint."""
from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from agentp_shared.config import db_settings
from agentp_auth import service
from agentp_shared import redis as shared_redis
from agentp_shared.models import User

_test_engine = create_async_engine(db_settings.url, echo=False, poolclass=NullPool)
_test_session_factory = async_sessionmaker(_test_engine, class_=AsyncSession, expire_on_commit=False)


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


class TestRenewApiKey:

    async def test_renew_api_key(self, db):
        created = await service.create_api_key(db, org_id="org-root", user_id="user-admin", name="Renew Me", expires_in_days=5)
        old_expires = created["expires_at"]
        renewed = await service.renew_api_key(db, org_id="org-root", key_id=created["id"], expires_in_days=30)
        assert renewed["ok"] is True
        assert renewed["key_id"] == created["id"]
        assert renewed["expires_at"] > old_expires

    async def test_renew_nonexistent_key(self, db):
        with pytest.raises(service.AuthError) as exc_info:
            await service.renew_api_key(db, org_id="org-root", key_id="nonexistent-id", expires_in_days=30)
        assert exc_info.value.code == "NOT_FOUND"

    async def test_renew_invalid_days(self, db):
        with pytest.raises(service.AuthError) as exc_info:
            await service.renew_api_key(db, org_id="org-root", key_id="any-id", expires_in_days=0)
        assert exc_info.value.code == "VALIDATION_ERROR"
