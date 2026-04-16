"""Billing service API tests - internal endpoints."""
import pytest
from httpx import AsyncClient, ASGITransport


@pytest.fixture(autouse=True)
def setup_billing():
    from ohent_billing.service import BillingService, init_billing
    init_billing()


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_health():
    from ohent_billing.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["service"] == "billing"


@pytest.mark.asyncio
async def test_summary():
    from ohent_billing.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/internal/billing/usage/summary?period=month")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "total_tokens" in data
        assert "total_cost" in data
        assert "by_model" in data
        assert "daily_trend" in data
        assert data["total_tokens"] > 0
        assert data["total_cost"] > 0


@pytest.mark.asyncio
async def test_summary_by_model():
    from ohent_billing.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/internal/billing/usage/summary?period=month")
        assert resp.status_code == 200
        by_model = resp.json()["data"]["by_model"]
        assert len(by_model) >= 1
        for entry in by_model:
            assert "model" in entry
            assert "tokens" in entry
            assert "cost" in entry
        model_names = {e["model"] for e in by_model}
        assert "gpt-4" in model_names
        assert "gpt-3.5-turbo" in model_names


@pytest.mark.asyncio
async def test_records_list():
    from ohent_billing.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/internal/billing/usage/records")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "total" in body
        assert "page" in body
        assert "page_size" in body
        assert body["total"] >= 5
        assert body["page"] == 1
        assert body["page_size"] == 20
        assert len(body["items"]) >= 5
        for item in body["items"]:
            assert "id" in item
            assert "time" in item
            assert "instance_name" in item
            assert "model" in item
            assert "input_tokens" in item
            assert "output_tokens" in item
            assert "cost" in item


@pytest.mark.asyncio
async def test_records_filter_by_instance_id():
    from ohent_billing.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/internal/billing/usage/records?instance_id=inst-001")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        for item in body["items"]:
            assert item["instance_name"] == "inst-001"


@pytest.mark.asyncio
async def test_records_filter_by_model():
    from ohent_billing.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/internal/billing/usage/records?model=gpt-4")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        for item in body["items"]:
            assert item["model"] == "gpt-4"


@pytest.mark.asyncio
async def test_records_pagination():
    from ohent_billing.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/internal/billing/usage/records?page=1&page_size=2")
        assert resp.status_code == 200
        body = resp.json()
        assert body["page"] == 1
        assert body["page_size"] == 2
        assert len(body["items"]) == 2
        assert body["total"] >= 5


@pytest.mark.asyncio
async def test_records_empty_filter():
    from ohent_billing.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/internal/billing/usage/records?instance_id=nonexistent")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["items"] == []
