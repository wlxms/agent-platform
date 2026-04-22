"""T4.3 — Tree browsing tests for memory assets."""
from __future__ import annotations

import pytest

from agentp_memory import service


_test_org_id = "org-1"


class TestBrowseTreeStructure:

    @pytest.mark.asyncio
    async def test_browse_tree_structure(self, db_session):
        await service.create_asset(db_session, path="/docs/readme.md", content="readme", org_id=_test_org_id)
        await service.create_asset(db_session, path="/docs/api.md", content="api", org_id=_test_org_id)
        await service.create_asset(db_session, path="/src/main.py", content="main", org_id=_test_org_id)
        result = await service.browse_tree(db_session, org_id=_test_org_id)
        assert len(result["paths"]) == 3
        assert "docs" in result["tree"]
        assert "src" in result["tree"]


class TestBrowseTreeWithPrefix:

    @pytest.mark.asyncio
    async def test_browse_tree_with_prefix(self, db_session):
        await service.create_asset(db_session, path="/docs/readme.md", content="readme", org_id=_test_org_id)
        await service.create_asset(db_session, path="/src/main.py", content="main", org_id=_test_org_id)
        result = await service.browse_tree(db_session, org_id=_test_org_id, path_prefix="/docs")
        assert len(result["paths"]) == 1
