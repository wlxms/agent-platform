"""Auth API v1 endpoints: login, refresh, logout, me."""
from __future__ import annotations

from fastapi import APIRouter, Request

from ohent_shared.responses import data_response, ok_response
from ohent_shared.security import decode_token

from ...schemas import LoginRequest, RefreshRequest
from ... import service

router = APIRouter(prefix="/internal/auth", tags=["auth"])


def _error_json(exc: service.AuthError) -> tuple[dict, int]:
    return {"code": exc.code, "message": exc.message, "details": exc.details}, exc.status_code


@router.post("/login")
async def login(req: LoginRequest):
    try:
        result = service.login(req.api_key)
    except service.AuthError as exc:
        body, status = _error_json(exc)
        from fastapi.responses import JSONResponse
        return JSONResponse(content=body, status_code=status)
    return data_response(result)


@router.post("/refresh")
async def refresh(req: RefreshRequest):
    try:
        result = service.refresh(req.refresh_token)
    except service.AuthError as exc:
        body, status = _error_json(exc)
        from fastapi.responses import JSONResponse
        return JSONResponse(content=body, status_code=status)
    return data_response(result)


@router.post("/logout")
async def logout():
    return ok_response()


@router.get("/me")
async def me(request: Request):
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        body, status = _error_json(service.AuthError(code="UNAUTHORIZED", message="Missing or invalid Authorization header"))
        from fastapi.responses import JSONResponse
        return JSONResponse(content=body, status_code=status)

    token = auth_header[7:]
    try:
        payload = decode_token(token)
    except Exception:
        body, status = _error_json(service.AuthError(code="UNAUTHORIZED", message="Invalid or expired token"))
        from fastapi.responses import JSONResponse
        return JSONResponse(content=body, status_code=status)

    if payload.get("type") != "access":
        body, status = _error_json(service.AuthError(code="UNAUTHORIZED", message="Not an access token"))
        from fastapi.responses import JSONResponse
        return JSONResponse(content=body, status_code=status)

    user_info = service.get_user_info(payload)
    return data_response(user_info)
