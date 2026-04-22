"""JWT token creation, decoding, and refresh."""
from __future__ import annotations
import uuid
from datetime import datetime, timedelta, timezone

import jwt

from .config import jwt_settings


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=jwt_settings.access_token_expire_minutes)
    )
    to_encode.update({
        "exp": expire,
        "jti": str(uuid.uuid4()),
        "type": "access",
    })
    return jwt.encode(to_encode, jwt_settings.secret_key, algorithm=jwt_settings.algorithm)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=jwt_settings.refresh_token_expire_days)
    to_encode.update({
        "exp": expire,
        "jti": str(uuid.uuid4()),
        "type": "refresh",
    })
    return jwt.encode(to_encode, jwt_settings.secret_key, algorithm=jwt_settings.algorithm)


def decode_token(token: str) -> dict:
    """Decode and validate JWT. Raises jwt.InvalidTokenError on failure."""
    return jwt.decode(token, jwt_settings.secret_key, algorithms=[jwt_settings.algorithm])

# ---------------------------------------------------------------------------
# RBAC Permission System
# ---------------------------------------------------------------------------

ALL_PERMISSIONS = [
    "agents:create",
    "agents:read",
    "agents:destroy",
    "agents:manage",
    "members:read",
    "members:manage",
    "billing:read",
    "billing:manage",
    "configs:manage",
    "approvals:read",
    "approvals:manage",
    "org:manage",
    "permissions:read",
    "roles:manage",
]

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "admin": ["*"],
    "manager": [
        "agents:create",
        "agents:read",
        "agents:manage",
        "members:read",
        "billing:read",
        "configs:manage",
        "approvals:read",
    ],
    "member": [
        "agents:create",
        "agents:read",
        "configs:manage",
    ],
}


def has_permission(user_permissions: list[str], required: str) -> bool:
    """Check if a user has a specific permission. '*' means all permissions."""
    if "*" in user_permissions:
        return True
    return required in user_permissions


def require_permission(permission: str):
    """FastAPI dependency that checks if the current user has a permission."""
    from fastapi import Depends, HTTPException, Request

    async def _check(request: Request):
        # Token is validated by upstream auth middleware
        user_perms = getattr(request.state, "permissions", [])
        if not has_permission(user_perms, permission):
            raise HTTPException(status_code=403, detail={
                "code": "FORBIDDEN",
                "message": f"Permission required: {permission}",
            })
        return True

    return Depends(_check)


def require_role(role: str):
    """FastAPI dependency that checks if the current user has a specific role."""
    from fastapi import Depends, HTTPException, Request

    async def _check(request: Request):
        user_role = getattr(request.state, "role", "")
        if user_role != role and user_role != "admin":
            raise HTTPException(status_code=403, detail={
                "code": "FORBIDDEN",
                "message": f"Role required: {role}",
            })
        return True

    return Depends(_check)
