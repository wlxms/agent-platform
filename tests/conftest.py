"""Shared test configuration — provides a session-scoped event loop so that
asyncpg and Redis connections survive across tests without
'Future attached to a different loop' errors.

Requires ``asyncio_mode = "auto"`` in pyproject.toml.
"""
from __future__ import annotations

import asyncio
import pytest

# All async tests/fixtures use the default (function-scoped) event loop.
pytestmark = pytest.mark.asyncio

# ---------------------------------------------------------------------------
# Fixed test API Key — used across ALL test scenarios and E2E verification.
# Corresponding Admin API Key seed: oh-admin-key-default
# Root org ID: org-root
# ---------------------------------------------------------------------------
TEST_API_KEY = "sk-3aa4613249a34bc6a54d14f561ca7597"
TEST_ADMIN_API_KEY = "oh-admin-key-default"
TEST_ROOT_ORG_ID = "org-root"


@pytest.fixture(scope="session")
def event_loop_policy():
    """Use the default policy; the loop itself is managed by pytest-asyncio."""
    return asyncio.get_event_loop_policy()


@pytest.fixture(scope="session")
def test_api_key() -> str:
    """Return the fixed test API Key for all test scenarios."""
    return TEST_API_KEY


@pytest.fixture(scope="session")
def test_admin_api_key() -> str:
    """Return the fixed admin API Key for admin-level test scenarios."""
    return TEST_ADMIN_API_KEY


# ---------------------------------------------------------------------------
# Function-scoped fixtures (use their own event loop per test)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
async def db_session():
    """Provide a clean async DB session per test function.

    Uses NullPool so each test gets a fresh connection that matches
    the function-scoped event loop (avoids 'attached to a different loop').
    Tables are created/dropped per invocation so tests are isolated.
    """
    from sqlalchemy.pool import NullPool
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

    from agentp_shared.models import Base
    from agentp_shared.config import db_settings

    test_db_url = f"{db_settings.url}_test"
    engine = create_async_engine(test_db_url, poolclass=NullPool, echo=False)

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with session_factory() as session:
            # Seed a default org so FK constraints on org_id are satisfied
            from agentp_shared.models import Organization
            from sqlalchemy import select
            existing = (await session.execute(
                select(Organization).where(Organization.id == "org-1")
            )).scalar_one_or_none()
            if not existing:
                session.add(Organization(id="org-1", name="Test Org"))
                await session.flush()
            await session.commit()
            yield session
    finally:
        await engine.dispose()


@pytest.fixture(scope="function")
async def authenticated_client():
    """Provide an httpx.AsyncClient with a valid admin JWT attached."""
    import httpx
    from agentp_shared.security import create_access_token

    token = create_access_token({
        "sub": "user-test-admin",
        "org_id": "org-root",
        "role": "admin",
        "permissions": ["*"],
    })

    async with httpx.AsyncClient(
        base_url="http://testserver",
        headers={"Authorization": f"Bearer {token}"},
    ) as client:
        yield client
