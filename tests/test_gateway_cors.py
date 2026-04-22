"""Tests for CORS middleware (T6.2)."""
import pytest


@pytest.mark.asyncio
async def test_cors_headers_present():
    from agentp_gateway.main import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    resp = client.options(
        "/api/v1/agents",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.status_code == 200
    assert "access-control-allow-origin" in resp.headers
