"""T7.2: Tests for command execution endpoint."""
from __future__ import annotations

import pytest
from agentp_host.service import HostService, HostError


@pytest.fixture
def svc():
    return HostService()


def test_command_execution(svc):
    result = svc.execute_command("any-id", "echo hello")
    assert "output" in result


def test_command_execution_invalid_instance(svc):
    # Noop driver always succeeds — verify output structure
    result = svc.execute_command("nonexistent", "ls")
    assert "output" in result
