"""Memory service tests - Wave 5."""
import pytest
from httpx import AsyncClient, ASGITransport

from agentp_memory.main import app


@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_create_asset():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/internal/memory/assets", json={
            "path": "test/hello.txt",
            "content": "Hello, World!",
            "content_type": "text/plain",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert data["data"]["path"] == "test/hello.txt"
        assert data["data"]["content_type"] == "text/plain"
        assert "created_at" in data["data"]
        assert "updated_at" in data["data"]


@pytest.mark.asyncio
async def test_get_asset():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create first
        await client.post("/internal/memory/assets", json={
            "path": "test/get_me.txt",
            "content": "fetch this",
        })
        # Get
        resp = await client.get("/internal/memory/assets/test/get_me.txt")
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["path"] == "test/get_me.txt"
        assert data["data"]["content"] == "fetch this"


@pytest.mark.asyncio
async def test_get_asset_not_found():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/internal/memory/assets/nonexistent/file.txt")
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_assets():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Service seeds 3 sample assets, so list should return at least 3
        resp = await client.get("/internal/memory/assets")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert len(data["items"]) >= 3
        for item in data["items"]:
            assert "path" in item
            assert "name" in item
            assert "type" in item


@pytest.mark.asyncio
async def test_list_assets_empty():
    """Listing with a path filter that matches nothing returns empty."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/internal/memory/assets", params={"path": "zzz_no_match"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []


@pytest.mark.asyncio
async def test_delete_asset():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create
        await client.post("/internal/memory/assets", json={
            "path": "test/to_delete.txt",
            "content": "bye",
        })
        # Delete
        resp = await client.delete("/internal/memory/assets/test/to_delete.txt")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
        # Confirm gone
        resp2 = await client.get("/internal/memory/assets/test/to_delete.txt")
        assert resp2.status_code == 404


@pytest.mark.asyncio
async def test_delete_asset_not_found():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.delete("/internal/memory/assets/nonexistent/gone.txt")
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_asset():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create
        await client.post("/internal/memory/assets", json={
            "path": "test/update_me.txt",
            "content": "original",
        })
        # Update same path
        resp = await client.post("/internal/memory/assets", json={
            "path": "test/update_me.txt",
            "content": "updated content",
            "content_type": "text/markdown",
        })
        assert resp.status_code == 200
        assert resp.json()["data"]["content_type"] == "text/markdown"

        # Verify content changed
        get_resp = await client.get("/internal/memory/assets/test/update_me.txt")
        assert get_resp.status_code == 200
        assert get_resp.json()["data"]["content"] == "updated content"


@pytest.mark.asyncio
async def test_list_assets_with_path_filter():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create two assets in different paths
        await client.post("/internal/memory/assets", json={
            "path": "docs/readme.md",
            "content": "# Docs",
        })
        await client.post("/internal/memory/assets", json={
            "path": "src/main.py",
            "content": "print('hello')",
        })
        # Filter by path
        resp = await client.get("/internal/memory/assets", params={"path": "docs"})
        assert resp.status_code == 200
        data = resp.json()
        assert all(item["path"].startswith("docs") for item in data["items"])
