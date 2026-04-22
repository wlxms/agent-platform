"""Health check aggregation across all platform services."""
from __future__ import annotations

import httpx
from typing import Any


async def check_service_health(url: str, timeout: float = 5.0) -> dict[str, Any]:
    """Probe a single service's /health endpoint."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(f"{url}/health")
            if resp.status_code == 200:
                return {"status": "ok", "detail": resp.json()}
            return {"status": "error", "code": resp.status_code}
    except (httpx.ConnectError, httpx.ConnectTimeout):
        return {"status": "unavailable"}
    except Exception:
        return {"status": "error"}


async def aggregate_health(
    services: dict[str, str], timeout: float = 5.0
) -> dict[str, Any]:
    """Check health of multiple services and return aggregated result."""
    results = {}
    for name, url in services.items():
        results[name] = await check_service_health(url, timeout)
    return results
