"""Error codes, status mapping, OHError exception, and error_response generator."""
from __future__ import annotations


class ErrorCode(str):
    """api-protocol.md §2.3 error codes."""

    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    API_DEPRECATED = "API_DEPRECATED"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    UPSTREAM_UNAVAILABLE = "UPSTREAM_UNAVAILABLE"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


class ErrorStatusMap:
    MAP: dict[str, int] = {
        ErrorCode.UNAUTHORIZED: 401,
        ErrorCode.FORBIDDEN: 403,
        ErrorCode.QUOTA_EXCEEDED: 403,
        ErrorCode.NOT_FOUND: 404,
        ErrorCode.CONFLICT: 409,
        ErrorCode.API_DEPRECATED: 410,
        ErrorCode.VALIDATION_ERROR: 422,
        ErrorCode.RATE_LIMITED: 429,
        ErrorCode.INTERNAL_ERROR: 500,
        ErrorCode.UPSTREAM_UNAVAILABLE: 502,
        ErrorCode.SERVICE_UNAVAILABLE: 503,
    }


def OHError(code: str, message: str, request_id: str = "", details: dict | None = None):  # type: ignore[misc]
    """Create an OHError-like dict for error responses (avoids FastAPI dependency in shared lib)."""
    status_code = ErrorStatusMap.MAP.get(code, 500)
    return {
        "status_code": status_code,
        "detail": {
            "code": code,
            "message": message,
            "request_id": request_id,
            "details": details or {},
        },
    }


def error_response(code: str, message: str, request_id: str = "", details: dict | None = None) -> dict:
    return {
        "code": code,
        "message": message,
        "request_id": request_id,
        "details": details or {},
    }
