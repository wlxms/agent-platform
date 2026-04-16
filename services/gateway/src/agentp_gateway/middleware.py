"""Gateway middleware: JWT auth, request_id injection, request forwarding."""
from __future__ import annotations

import uuid

import httpx
import jwt
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from agentp_shared.config import SCHEDULER_URL
from agentp_shared.security import decode_token
from starlette.middleware.base import BaseHTTPMiddleware

# Paths that don't require JWT auth
PUBLIC_PATHS = {"/health", "/api/v1/auth/login", "/docs", "/openapi.json"}


def _error_body(code: str, message: str, request_id: str, details: dict | None = None) -> dict:
    """Build error response body matching the API protocol."""
    return {
        "code": code,
        "message": message,
        "request_id": request_id,
        "details": details or {},
    }


class GatewayMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        path = request.url.path

        # Health check - pass through, add request_id
        if path == "/health":
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response

        # Public paths - forward to scheduler without JWT
        if path in PUBLIC_PATHS or path.startswith("/docs"):
            return await self._forward_public(request, request_id)

        # JWT Authentication
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content=_error_body(
                    "UNAUTHORIZED",
                    "Missing or invalid authorization header",
                    request_id,
                ),
                headers={"X-Request-ID": request_id},
            )

        token = auth_header[7:]
        try:
            payload = decode_token(token)
        except jwt.ExpiredSignatureError:
            return JSONResponse(
                status_code=401,
                content=_error_body(
                    "UNAUTHORIZED",
                    "Token has expired",
                    request_id,
                    {"expired": True},
                ),
                headers={"X-Request-ID": request_id},
            )
        except jwt.InvalidTokenError:
            return JSONResponse(
                status_code=401,
                content=_error_body(
                    "UNAUTHORIZED",
                    "Invalid token",
                    request_id,
                ),
                headers={"X-Request-ID": request_id},
            )

        # Inject user info into request state for downstream
        request.state.user_id = payload.get("sub", "")
        request.state.org_id = payload.get("org_id", "")
        request.state.role = payload.get("role", "user")
        request.state.permissions = payload.get("permissions", [])

        # Forward to scheduler
        return await self._forward_to_scheduler(request, request_id, payload)

    async def _forward_public(self, request: Request, request_id: str) -> Response:
        """Forward public (no-auth) requests to scheduler."""
        target_url = f"{SCHEDULER_URL}{request.url.path}"
        headers = {
            "X-Internal-Call": "true",
            "X-Request-ID": request_id,
            "Content-Type": request.headers.get("content-type", "application/json"),
        }
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
                response = JSONResponse(
                    status_code=resp.status_code,
                    content=resp.json(),
                )
                response.headers["X-Request-ID"] = request_id
                return response
        except Exception:
            return JSONResponse(
                status_code=502,
                content=_error_body(
                    "UPSTREAM_UNAVAILABLE",
                    "Scheduler unavailable",
                    request_id,
                ),
                headers={"X-Request-ID": request_id},
            )

    async def _forward_to_scheduler(
        self, request: Request, request_id: str, payload: dict
    ) -> Response:
        target_url = f"{SCHEDULER_URL}{request.url.path}"

        headers = {
            "X-Internal-Call": "true",
            "X-Request-ID": request_id,
            "X-Tenant-ID": payload.get("org_id", ""),
            "X-User-ID": payload.get("sub", ""),
            "X-Org-ID": payload.get("org_id", ""),
            "Content-Type": request.headers.get("content-type", "application/json"),
        }
        # Forward Authorization header for downstream services that need it
        auth_header = request.headers.get("authorization", "")
        if auth_header:
            headers["Authorization"] = auth_header

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

                response = JSONResponse(
                    status_code=resp.status_code,
                    content=resp.json(),
                )
                response.headers["X-Request-ID"] = request_id
                return response
        except Exception:
            return JSONResponse(
                status_code=502,
                content=_error_body(
                    "UPSTREAM_UNAVAILABLE",
                    "Scheduler service unavailable",
                    request_id,
                    {"service": "scheduler"},
                ),
                headers={"X-Request-ID": request_id},
            )
