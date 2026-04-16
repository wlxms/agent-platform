"""Service proxy - forwards requests to backend services."""
import httpx
from fastapi import Request
from fastapi.responses import JSONResponse

from ohent_shared.config import AUTH_URL, HOST_URL, MEMORY_URL, MARKET_URL, BILLING_URL
from ohent_shared.errors import error_response

# Route table: path prefix -> (backend service URL, internal prefix)
ROUTE_TABLE: dict[str, tuple[str, str]] = {
    "/api/v1/auth": (AUTH_URL, "/internal/auth"),
    "/api/v1/agents": (HOST_URL, "/internal/agents"),
    "/api/v1/memory": (MEMORY_URL, "/internal/memory"),
    "/api/v1/market": (MARKET_URL, "/internal/market"),
    "/api/v1/billing": (BILLING_URL, "/internal/billing"),
}

# Task status store (in-memory for skeleton)
_tasks: dict[str, dict] = {}


async def proxy_request(request: Request, path: str) -> JSONResponse:
    """Forward request to the appropriate backend service."""
    # Find matching backend
    target_url = None
    for prefix, (url, internal_prefix) in sorted(
        ROUTE_TABLE.items(), key=lambda x: -len(x[0])
    ):
        if path.startswith(prefix):
            suffix = path[len(prefix) :]
            target_url = f"{url}{internal_prefix}{suffix}"
            break

    if target_url is None:
        return JSONResponse(
            status_code=404,
            content=error_response(
                "NOT_FOUND", "No route found", request.headers.get("x-request-id", "")
            ),
        )

    # Build headers - forward internal call headers
    headers = {
        "X-Internal-Call": "true",
        "X-Request-ID": request.headers.get("x-request-id", ""),
        "X-Tenant-ID": request.headers.get("x-org-id", ""),
        "X-User-ID": request.headers.get("x-user-id", ""),
        "X-Org-ID": request.headers.get("x-org-id", ""),
        "Content-Type": "application/json",
    }
    # Forward Authorization header for downstream auth checks
    auth_header = request.headers.get("authorization", "")
    if auth_header:
        headers["Authorization"] = auth_header

    # Forward query params
    params = dict(request.query_params)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            body = await request.body()
            resp = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                params=params,
                content=body if body else None,
            )

            return JSONResponse(
                status_code=resp.status_code,
                content=resp.json(),
            )
    except httpx.ConnectError:
        return JSONResponse(
            status_code=502,
            content=error_response(
                "UPSTREAM_UNAVAILABLE",
                "Backend service unavailable",
                request.headers.get("x-request-id", ""),
                {"service": target_url},
            ),
        )
    except Exception:
        return JSONResponse(
            status_code=502,
            content=error_response(
                "UPSTREAM_UNAVAILABLE",
                "Backend service unavailable",
                request.headers.get("x-request-id", ""),
                {"service": target_url},
            ),
        )


async def get_task_status(task_id: str, request_id: str = "") -> dict:
    """Get task status. Skeleton: returns completed for unknown tasks."""
    if task_id in _tasks:
        return {"data": _tasks[task_id]}
    return {"data": {"id": task_id, "status": "completed", "result": None}}
