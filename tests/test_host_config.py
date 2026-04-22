"""T7.3: Tests for skills, MCP, and config management."""
from __future__ import annotations

import pytest
from agentp_host.service import HostService


@pytest.fixture
def svc():
    return HostService()


def test_add_skill(svc):
    result = svc.add_skill("any-id", "search")
    assert result["ok"] is True


def test_add_mcp(svc):
    result = svc.add_mcp("any-id", name="gh", transport="http", config={"url": "http://x"})
    assert result["ok"] is True


def test_update_config(svc):
    result = svc.update_config("any-id", system_prompt="New prompt", permission_mode="strict")
    assert result["ok"] is True
