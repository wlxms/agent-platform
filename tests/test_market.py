"""Tests for Market service (Wave 5)."""
import pytest
from httpx import AsyncClient, ASGITransport
from ohent_market.main import app


@pytest.fixture(autouse=True)
def _reset_service():
    """Reset singleton before each test."""
    from ohent_market.api.v1.templates import reset_service
    reset_service()


@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_list_templates():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/internal/market/templates")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "total" in body
        assert body["total"] == 3
        assert body["page"] == 1
        assert body["page_size"] == 20
        assert len(body["items"]) == 3
        for item in body["items"]:
            assert "id" in item
            assert "name" in item
            assert "description" in item
            assert "category" in item
            assert "skills" in item
            assert "mcp" in item
            assert "usage_count" in item


@pytest.mark.asyncio
async def test_list_templates_with_category_filter():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/internal/market/templates?category=coding")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["category"] == "coding"


@pytest.mark.asyncio
async def test_list_templates_with_keyword():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/internal/market/templates?keyword=research")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        for item in body["items"]:
            assert "research" in item["name"].lower() or "research" in item["description"].lower()


@pytest.mark.asyncio
async def test_get_template():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/internal/market/templates/tpl-001")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        tpl = body["data"]
        assert tpl["id"] == "tpl-001"
        assert "name" in tpl
        assert "description" in tpl
        assert "category" in tpl
        assert "scenario" in tpl
        assert "skills" in tpl
        assert "mcp" in tpl
        assert "resource_spec" in tpl
        assert "usage_count" in tpl


@pytest.mark.asyncio
async def test_get_template_not_found():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/internal/market/templates/nonexistent-id")
        assert resp.status_code == 404
        body = resp.json()
        assert body["detail"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_list_skills():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/internal/market/skills")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert body["total"] == 2
        for item in body["items"]:
            assert "id" in item
            assert "name" in item
            assert "description" in item
            assert "author" in item
            assert "version" in item


@pytest.mark.asyncio
async def test_list_mcps():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/internal/market/mcps")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert body["total"] == 1
        item = body["items"][0]
        assert "id" in item
        assert "name" in item
        assert "transport" in item
        assert "description" in item


@pytest.mark.asyncio
async def test_pagination():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # page=1, page_size=1 → only 1 item, total=3
        resp = await client.get("/internal/market/templates?page=1&page_size=1")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) == 1
        assert body["total"] == 3
        assert body["page"] == 1
        assert body["page_size"] == 1

        # page=2, page_size=2 → 1 item
        resp2 = await client.get("/internal/market/templates?page=2&page_size=2")
        body2 = resp2.json()
        assert len(body2["items"]) == 1
        assert body2["total"] == 3
        assert body2["page"] == 2
