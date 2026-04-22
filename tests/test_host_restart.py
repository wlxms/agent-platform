"""T7.1: Tests for agent restart and batch restart/destroy."""
from __future__ import annotations

import pytest
from agentp_host.service import HostService, HostError


@pytest.fixture
def svc():
    return HostService()


def test_restart_agent(svc):
    result = svc.restart_instance("any-id")
    assert result["ok"] is True


def test_batch_restart(svc):
    result = svc.batch_restart(["id-1", "id-2"])
    assert result["ok"] is True
    assert len(result["results"]) == 2


def test_batch_destroy(svc):
    result = svc.batch_destroy(["id-1", "id-2"])
    assert result["ok"] is True
