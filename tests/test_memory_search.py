"""T4.2 — Keyword search tests for memory assets."""
from __future__ import annotations

import pytest

from agentp_memory import service


_test_org_id = "org-1"


class TestSearchAssetsByKeyword:

    @pytest.mark.asyncio
    async def test_search_assets_by_keyword(self, db_session):
        await service.create_asset(db_session, path="/docs/readme.md", content="This is the project README", org_id=_test_org_id)
        await service.create_asset(db_session, path="/docs/changelog.md", content="Version 2.0 changes", org_id=_test_org_id)
        result = await service.search_assets(db_session, keyword="README", org_id=_test_org_id)
        assert result["total"] == 1
        assert result["items"][0]["path"] == "/docs/readme.md"


class TestSearchNoResults:

    @pytest.mark.asyncio
    async def test_search_no_results(self, db_session):
        result = await service.search_assets(db_session, keyword="nonexistent", org_id=_test_org_id)
        assert result["total"] == 0
        assert result["items"] == []
