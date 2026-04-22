"""Tests for RBAC middleware primitives."""
import pytest


def test_admin_has_all_permissions():
    from agentp_shared.security import has_permission
    perms = ["*"]
    assert has_permission(perms, "agents:create") is True
    assert has_permission(perms, "agents:destroy") is True
    assert has_permission(perms, "billing:manage") is True
    assert has_permission(perms, "nonexistent:perm") is True


def test_manager_has_limited_permissions():
    from agentp_shared.security import has_permission, ROLE_PERMISSIONS
    perms = ROLE_PERMISSIONS["manager"]
    assert has_permission(perms, "agents:create") is True
    assert has_permission(perms, "agents:read") is True
    assert has_permission(perms, "agents:manage") is True
    assert has_permission(perms, "members:read") is True
    assert has_permission(perms, "billing:read") is True
    assert has_permission(perms, "configs:manage") is True
    assert has_permission(perms, "approvals:read") is True
    assert has_permission(perms, "billing:manage") is False
    assert has_permission(perms, "agents:destroy") is False


def test_member_has_basic_permissions():
    from agentp_shared.security import has_permission, ROLE_PERMISSIONS
    perms = ROLE_PERMISSIONS["member"]
    assert has_permission(perms, "agents:create") is True
    assert has_permission(perms, "agents:read") is True
    assert has_permission(perms, "configs:manage") is True
    assert has_permission(perms, "agents:destroy") is False
    assert has_permission(perms, "billing:read") is False


def test_permission_list_complete():
    from agentp_shared.security import ALL_PERMISSIONS
    expected = [
        "agents:create", "agents:read", "agents:destroy", "agents:manage",
        "members:read", "members:manage",
        "billing:read", "billing:manage",
        "configs:manage",
        "approvals:read", "approvals:manage",
        "org:manage",
        "permissions:read", "roles:manage",
    ]
    assert sorted(ALL_PERMISSIONS) == sorted(expected)
    assert len(ALL_PERMISSIONS) == 14


def test_role_permissions_mapping():
    from agentp_shared.security import ROLE_PERMISSIONS
    assert "*" in ROLE_PERMISSIONS["admin"]
    assert len(ROLE_PERMISSIONS["manager"]) == 7
    assert len(ROLE_PERMISSIONS["member"]) == 3
    assert set(ROLE_PERMISSIONS.keys()) == {"admin", "manager", "member"}


def test_require_permission_dependency():
    from fastapi import Depends
    from agentp_shared.security import require_permission
    dep = require_permission("agents:create")
    assert type(dep).__name__ == "Depends"
    assert dep.dependency is not None


def test_require_role_dependency():
    from fastapi import Depends
    from agentp_shared.security import require_role
    dep = require_role("admin")
    assert type(dep).__name__ == "Depends"
    assert dep.dependency is not None
