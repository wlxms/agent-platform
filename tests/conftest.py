"""Shared test configuration — provides a session-scoped event loop so that
asyncpg and Redis connections survive across tests without
'Future attached to a different loop' errors.

Requires ``asyncio_mode = "auto"`` in pyproject.toml.
"""
from __future__ import annotations

import asyncio
import pytest

# All async tests/fixtures default to the *session* event loop.
pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.fixture(scope="session")
def event_loop_policy():
    """Use the default policy; the loop itself is managed by pytest-asyncio."""
    return asyncio.get_event_loop_policy()
