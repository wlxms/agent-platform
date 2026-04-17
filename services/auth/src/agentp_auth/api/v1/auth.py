"""Auth API v1 endpoints: login, refresh, logout, me, org/user/api-key management."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Query

from agentp_shared.db import get_db
from agentp_shared.responses import data_response, ok_response, list_response
from agentp_shared.security import decode_token
from agentp_shared.schemas import PaginatedQuery
from sqlalchemy.ext.asyncio import AsyncSession

from ...schemas import LoginRequest, RefreshRequest, CreateOrgRequest, CreateApiKeyRequest
from ... import service

router = APIRouter(prefix="/internal/auth", tags=["auth"])


def _error_json(exc: service.AuthError) -> tuple[dict, int]:
    return {"code": exc.code, "message": exc.message, "details": exc.details}, exc.status_code


# --- Auth endpoints ---

@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        result = await service.login(req.api_key, db)
    except service.AuthError as exc:
        from fastapi.responses import JSONResponse
        body, status = _error_json(exc)
        return JSONResponse(content=body, status_code=status)
    return data_response(result)


@router.post("/refresh")
async def refresh(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        result = await service.refresh(req.refresh_token, db)
    except service.AuthError as exc:
        from fastapi.responses import JSONResponse
        body, status = _error_json(exc)
        return JSONResponse(content=body, status_code=status)
    return data_response(result)


@router.post("/logout")
async def logout(request: Request):
    # Try to get tokens from body or headers
    auth_header = request.headers.get("authorization", "")
    refresh_jti = None
    access_jti = None

    if auth_header.startswith("Bearer "):
        try:
            payload = decode_token(auth_header[7:])
            access_jti = payload.get("jti")
        except Exception:
            pass

    await service.logout(refresh_token_str=None, access_token_jti=access_jti)
    return ok_response()


@router.get("/me")
async def me(request: Request, db: AsyncSession = Depends(get_db)):
    auth_header = request.headers.get("authorization", "")
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

    user_info = await service.get_user_info(payload, db)
    return data_response(user_info)


# --- Organization management ---

@router.get("/org/tree")
async def org_tree(db: AsyncSession = Depends(get_db), depth: int = Query(default=3, ge=1, le=10)):
    tree = await service.get_org_tree(db, depth=depth)
    return data_response(tree)


@router.get("/org/{org_id}")
async def get_org(org_id: str, db: AsyncSession = Depends(get_db)):
    org = await service.get_organization(db, org_id)
    if org is None:
        body, status = _error_json(service.AuthError(code="NOT_FOUND", message="Organization not found"))
        from fastapi.responses import JSONResponse
        return JSONResponse(content=body, status_code=status)
    return data_response(org)


@router.post("/org")
async def create_org(req: CreateOrgRequest, db: AsyncSession = Depends(get_db)):
    result = await service.create_organization(db, name=req.name, parent_id=req.parent_id, plan=req.plan)
    return data_response(result)


@router.get("/org/{org_id}/members")
async def list_members(org_id: str, db: AsyncSession = Depends(get_db), page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100), role: str | None = None):
    result = await service.list_org_members(db, org_id, page=page, page_size=page_size, role=role)
    return list_response(**result)


# --- API Key management ---

@router.get("/api-keys")
async def list_api_keys(request: Request, db: AsyncSession = Depends(get_db), page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100)):
    # Get org_id from JWT token in header
    auth_header = request.headers.get("authorization", "")
    org_id = ""
    if auth_header.startswith("Bearer "):
        try:
            payload = decode_token(auth_header[7:])
            org_id = payload.get("org_id", "")
        except Exception:
            pass

    if not org_id:
        body, status = _error_json(service.AuthError(code="UNAUTHORIZED", message="Cannot determine organization"))
        from fastapi.responses import JSONResponse
        return JSONResponse(content=body, status_code=status)

    result = await service.list_api_keys(db, org_id=org_id, page=page, page_size=page_size)
    return list_response(**result)


@router.post("/api-keys")
async def create_api_key(req: CreateApiKeyRequest, request: Request, db: AsyncSession = Depends(get_db)):
    auth_header = request.headers.get("authorization", "")
    user_id = ""
    org_id = ""
    if auth_header.startswith("Bearer "):
        try:
            payload = decode_token(auth_header[7:])
            user_id = payload.get("sub", "")
            org_id = payload.get("org_id", "")
        except Exception:
            pass

    try:
        result = await service.create_api_key(
            db=db, org_id=org_id, user_id=user_id,
            name=req.name,
            permissions=req.permissions,
            expires_in_days=req.expires_in_days,
        )
    except service.AuthError as exc:
        from fastapi.responses import JSONResponse
        body_resp, status = _error_json(exc)
        return JSONResponse(content=body_resp, status_code=status)
    return data_response(result)


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(key_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    auth_header = request.headers.get("authorization", "")
    org_id = ""
    if auth_header.startswith("Bearer "):
        try:
            payload = decode_token(auth_header[7:])
            org_id = payload.get("org_id", "")
        except Exception:
            pass

    try:
        result = await service.revoke_api_key(db, org_id=org_id, key_id=key_id)
    except service.AuthError as exc:
        from fastapi.responses import JSONResponse
        body_resp, status = _error_json(exc)
        return JSONResponse(content=body_resp, status_code=status)
    return ok_response()
