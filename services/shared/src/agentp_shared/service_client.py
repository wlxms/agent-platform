"""Inter-service HTTP call wrapper."""
from __future__ import annotations

from typing import Any

import httpx


class ServiceClient:
    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=timeout)

    async def call(
        self,
        method: str,
        path: str,
        ctx: dict | None = None,
        json: dict | None = None,
        params: dict | None = None,
    ) -> dict:
        headers = {
            "X-Internal-Call": "true",
            "X-Request-ID": (ctx or {}).get("request_id", ""),
            "X-Tenant-ID": (ctx or {}).get("org_id", ""),
            "X-User-ID": (ctx or {}).get("user_id", ""),
            "X-Org-ID": (ctx or {}).get("org_id", ""),
        }
        resp = await self._client.request(method, path, headers=headers, json=json, params=params)
        return resp.json()

    async def close(self) -> None:
        await self._client.aclose()
