"""T4.1 — Binary upload/download tests for memory assets."""
from __future__ import annotations

import pytest

from agentp_memory import service


_test_org_id = "org-1"


class TestUploadBinaryAsset:

    @pytest.mark.asyncio
    async def test_upload_binary_asset(self, db_session):
        content = b"Hello binary world"
        result = await service.upload_binary_asset(
            db_session, path="/test/binary.bin", content=content,
            content_type="application/octet-stream", org_id=_test_org_id,
        )
        assert result["ok"] is True
        assert result["size_bytes"] == len(content)


class TestDownloadBinaryAsset:

    @pytest.mark.asyncio
    async def test_download_binary_asset(self, db_session):
        content = b"binary content here"
        await service.upload_binary_asset(
            db_session, path="/test/dl.bin", content=content,
            content_type="application/octet-stream", org_id=_test_org_id,
        )
        result = await service.download_binary_asset(db_session, path="/test/dl.bin", org_id=_test_org_id)
        assert result["content"] == content
        assert result["content_type"] == "application/octet-stream"


class TestDownloadNonexistent:

    @pytest.mark.asyncio
    async def test_download_nonexistent_returns_none(self, db_session):
        result = await service.download_binary_asset(db_session, path="/nonexistent", org_id=_test_org_id)
        assert result is None
