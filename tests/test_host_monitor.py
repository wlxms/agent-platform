"""T7.4: Tests for monitor stats and memory tree."""
from __future__ import annotations

import pytest
from agentp_host.service import HostService


@pytest.fixture
def svc():
    return HostService()


def test_get_monitor_stats(svc):
    result = svc.get_monitor_stats("any-id")
    assert "cpu_percent" in result
    assert "memory_mb" in result
    assert "total_tokens" in result


def test_get_memory_tree(svc):
    result = svc.get_memory_tree("any-id")
    assert "paths" in result
    assert "tree" in result
