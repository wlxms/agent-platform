"""T5.1 — Health check aggregation tests."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_aggregate_health_all_services():
    from agentp_scheduler.health import aggregate_health

    result = await aggregate_health(
        services={
            "auth": "http://localhost:8001",
            "host": "http://localhost:8002",
            "market": "http://localhost:8005",
        }
    )
    assert "auth" in result
    assert "host" in result
    assert result["auth"]["status"] in ("ok", "unavailable", "error")


async def test_aggregate_health_timeout():
    from agentp_scheduler.health import aggregate_health

    result = await aggregate_health(
        services={"slow": "http://localhost:9999"}, timeout=0.1
    )
    assert result["slow"]["status"] == "unavailable"
