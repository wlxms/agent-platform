"""Tests for permissions and roles read endpoints."""
from __future__ import annotations

import pytest
from agentp_shared.security import ALL_PERMISSIONS, ROLE_PERMISSIONS
from agentp_auth import service


class TestGetPermissions:

    def test_get_permissions(self):
        result = service.get_permissions()
        assert len(result) == 14
        assert any(p["id"] == "agents:create" for p in result)
        assert any(p["id"] == "roles:manage" for p in result)

    def test_get_permissions_all_have_ids(self):
        result = service.get_permissions()
        assert all("id" in p and "description" in p for p in result)


class TestGetRoles:

    def test_get_roles(self):
        result = service.get_roles()
        assert len(result) == 3
        role_names = {r["name"] for r in result}
        assert "admin" in role_names
        assert "manager" in role_names
        assert "member" in role_names

    def test_get_roles_admin_has_star(self):
        result = service.get_roles()
        admin_role = next(r for r in result if r["name"] == "admin")
        assert admin_role["permissions"] == ["*"]

    def test_get_roles_manager_permissions(self):
        result = service.get_roles()
        manager_role = next(r for r in result if r["name"] == "manager")
        assert len(manager_role["permissions"]) == 7
