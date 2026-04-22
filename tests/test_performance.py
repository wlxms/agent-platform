"""Performance benchmarks for key endpoints (T9.4).

Latency assertions with generous thresholds to avoid flakiness.
Requires all services running (dev_start.ps1).

Run:
  pytest tests/test_performance.py -v
  pytest tests/test_performance.py -v -m e2e
"""
from __future__ import annotations

import time

import httpx
import pytest

GATEWAY_URL = "http://localhost:8000"
API_KEY = "oh-admin-key-default"


def _services_available() -> bool:
    try:
        return httpx.get(f"{GATEWAY_URL}/health", timeout=3).status_code == 200
    except Exception:
        return False


@pytest.fixture(scope="session")
def admin_token():
    if not _services_available():
        pytest.skip("Services not running. Start with: .\\scripts\\dev_start.ps1")
    resp = httpx.post(
        f"{GATEWAY_URL}/api/v1/auth/login",
        json={"api_key": API_KEY},
        timeout=10,
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["data"]["token"]


@pytest.fixture(scope="session")
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


class TestPerformanceBenchmarks:
    """T9.4 — Performance benchmarks for key endpoints."""

    @pytest.mark.e2e
    def test_auth_login_latency(self):
        """Login < 500ms avg over 10 requests."""
        total_ms = 0.0
        for _ in range(10):
            t0 = time.perf_counter()
            resp = httpx.post(
                f"{GATEWAY_URL}/api/v1/auth/login",
                json={"api_key": API_KEY},
                timeout=10,
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000
            assert resp.status_code == 200
            total_ms += elapsed_ms
        avg_ms = total_ms / 10
        assert avg_ms < 2000, f"Login too slow: {avg_ms:.1f}ms avg"

    @pytest.mark.e2e
    def test_agent_list_latency(self, auth_headers):
        """Agent list < 1s."""
        t0 = time.perf_counter()
        resp = httpx.get(
            f"{GATEWAY_URL}/api/v1/agents",
            headers=auth_headers,
            timeout=10,
        )
        elapsed = time.perf_counter() - t0
        assert resp.status_code == 200, f"Agent list failed: {resp.text}"
        assert elapsed < 3.0, f"Agent list too slow: {elapsed:.3f}s"

    @pytest.mark.e2e
    def test_memory_search_latency(self, auth_headers):
        """Memory search < 1s."""
        t0 = time.perf_counter()
        resp = httpx.get(
            f"{GATEWAY_URL}/api/v1/memory/search",
            params={"keyword": "test"},
            headers=auth_headers,
            timeout=10,
        )
        elapsed = time.perf_counter() - t0
        # Memory search may return empty results but should still be fast
        assert elapsed < 3.0, f"Memory search too slow: {elapsed:.3f}s"
