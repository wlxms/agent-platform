"""Gateway middleware: JWT auth, request_id injection, request forwarding,
rate limiting, circuit breaker, audit logging."""
from __future__ import annotations

import time
import uuid

import httpx
import jwt
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from agentp_shared.config import SCHEDULER_URL
from agentp_shared.security import decode_token
from starlette.middleware.base import BaseHTTPMiddleware

from .rate_limit import RateLimiter
from .circuit_breaker import CircuitBreaker

# Paths that don't require JWT auth
PUBLIC_PATHS = {"/health", "/api/v1/auth/login", "/docs", "/openapi.json"}
PUBLIC_PREFIXES = {"/api/v1/agents/", "/docs"}

# Shared rate limiter and circuit breaker instances
rate_limiter = RateLimiter(max_requests=100, window_seconds=60)
circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=30)


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

        # CORS preflight requests — must be handled BEFORE any other processing
        if request.method == "OPTIONS":
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response

        # Health check - pass through, add request_id
        if path == "/health":
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response

        # Public paths - forward to scheduler without JWT
        if path in PUBLIC_PATHS or any(path.startswith(p) for p in PUBLIC_PREFIXES):
            # WebSocket stub paths should be handled by the router, not forwarded
            if "/stream" in path:
                response = await call_next(request)
                response.headers["X-Request-ID"] = request_id
                return response
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

        # Rate limiting (after auth, keyed by org_id for multi-tenant fairness)
        client_id = payload.get("org_id", request.client.host if request.client else "unknown")
        if not rate_limiter.is_allowed(client_id):
            remaining = rate_limiter.get_remaining(client_id)
            return JSONResponse(
                status_code=429,
                content=_error_body(
                    "RATE_LIMITED",
                    "Too many requests",
                    request_id,
                    {"retry_after": rate_limiter.window_seconds},
                ),
                headers={
                    "X-Request-ID": request_id,
                    "X-RateLimit-Remaining": str(remaining),
                    "Retry-After": str(rate_limiter.window_seconds),
                },
            )

        # Inject user info into request state for downstream
        request.state.user_id = payload.get("sub", "")
        request.state.org_id = payload.get("org_id", "")
        request.state.role = payload.get("role", "user")
        request.state.permissions = payload.get("permissions", [])

        # Forward to scheduler (with audit logging)
        import time as _time
        remaining = rate_limiter.get_remaining(client_id)
        t0 = _time.perf_counter()
        resp = await self._forward_to_scheduler(request, request_id, payload)
        latency_ms = int((_time.perf_counter() - t0) * 1000)
        resp.headers["X-RateLimit-Remaining"] = str(remaining)
        # Audit log (non-critical, log errors)
        try:
            from agentp_shared.db import async_session_factory
            from .audit import write_audit_log
            async with async_session_factory() as db:
                await write_audit_log(
                    db, method=request.method, path=request.url.path,
                    status_code=resp.status_code, latency_ms=latency_ms,
                    source_ip=request.client.host if request.client else "",
                    org_id=payload.get("org_id", ""),
                    request_id=request_id,
                    user_id=payload.get("sub", ""),
                )
        except Exception:
            pass
        return resp

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
                # Add CORS headers for public endpoints
                origin = request.headers.get("origin", "")
                if origin:
                    response.headers["Access-Control-Allow-Origin"] = origin
                    response.headers["Access-Control-Allow-Credentials"] = "true"
                    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
                    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
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
        # Circuit breaker check
        if not circuit_breaker.is_available("scheduler"):
            return JSONResponse(
                status_code=503,
                content=_error_body(
                    "SERVICE_UNAVAILABLE",
                    "Scheduler service is temporarily unavailable",
                    request_id,
                    {"service": "scheduler"},
                ),
                headers={"X-Request-ID": request_id},
            )

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
                # Add CORS headers
                origin = request.headers.get("origin", "")
                if origin:
                    response.headers["Access-Control-Allow-Origin"] = origin
                    response.headers["Access-Control-Allow-Credentials"] = "true"
                    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
                    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
                circuit_breaker.record_success("scheduler")
                return response
        except Exception:
            circuit_breaker.record_failure("scheduler")
            error_response = JSONResponse(
                status_code=502,
                content=_error_body(
                    "UPSTREAM_UNAVAILABLE",
                    "Scheduler unavailable",
                    request_id,
                ),
                headers={"X-Request-ID": request_id},
            )
            origin = request.headers.get("origin", "")
            if origin:
                error_response.headers["Access-Control-Allow-Origin"] = origin
                error_response.headers["Access-Control-Allow-Credentials"] = "true"
            return error_response
