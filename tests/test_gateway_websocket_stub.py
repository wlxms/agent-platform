"""Tests for WebSocket stub endpoint (T6.5)."""
import pytest


@pytest.mark.asyncio
async def test_websocket_returns_501():
    from fastapi.testclient import TestClient
    from agentp_gateway.main import app
    client = TestClient(app)
    # WebSocket endpoints return 501 via HTTP
    resp = client.get("/api/v1/agents/test-id/stream")
    assert resp.status_code == 501
    data = resp.json()
    assert data["code"] == "NOT_IMPLEMENTED"
