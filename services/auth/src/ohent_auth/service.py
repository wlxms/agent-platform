"""Auth service layer: API key auth, JWT token creation, user lookup."""
from datetime import datetime, timedelta, timezone

from ohent_shared.security import create_access_token, create_refresh_token, decode_token
from ohent_shared.config import jwt_settings

_API_KEYS: dict[str, dict] = {}


def init_api_keys(keys: dict[str, dict] | None = None):
    global _API_KEYS
    _API_KEYS = keys or {
        "oh-admin-key": {
            "id": "user-admin",
            "name": "Admin",
            "role": "admin",
            "org_id": "root",
            "permissions": ["*"],
        },
        "oh-org-admin-key": {
            "id": "user-org-admin",
            "name": "Org Admin",
            "role": "org_admin",
            "org_id": "org-001",
            "permissions": ["agent:manage", "user:manage", "billing:read"],
        },
        "oh-user-key": {
            "id": "user-001",
            "name": "Demo User",
            "role": "user",
            "org_id": "org-001",
            "permissions": ["agent:manage"],
        },
    }


def authenticate_api_key(api_key: str) -> dict | None:
    return _API_KEYS.get(api_key)


class AuthError(Exception):
    """Raised when authentication fails."""

    def __init__(self, code: str, message: str, details: dict | None = None):
        from ohent_shared.errors import ErrorStatusMap
        self.code = code
        self.message = message
        self.details = details or {}
        self.status_code = ErrorStatusMap.MAP.get(code, 500)


def login(api_key: str) -> dict:
    user_data = authenticate_api_key(api_key)
    if user_data is None:
        raise AuthError(code="UNAUTHORIZED", message="Invalid API key")

    token_data = {
        "sub": user_data["id"],
        "org_id": user_data["org_id"],
        "role": user_data["role"],
        "permissions": user_data.get("permissions", []),
    }

    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=jwt_settings.access_token_expire_minutes,
    )

    return {
        "token": access_token,
        "refresh_token": refresh_token,
        "expires_at": expires_at.isoformat(),
        "user": {
            "id": user_data["id"],
            "name": user_data["name"],
            "role": user_data["role"],
            "org_id": user_data["org_id"],
            "permissions": user_data.get("permissions", []),
        },
    }


def refresh(refresh_token_str: str) -> dict:
    try:
        payload = decode_token(refresh_token_str)
    except Exception:
        raise AuthError(
            code="UNAUTHORIZED",
            message="Invalid or expired refresh token",
            details={"refresh_expired": True},
        )

    if payload.get("type") != "refresh":
        raise AuthError(code="UNAUTHORIZED", message="Not a refresh token")

    token_data = {k: v for k, v in payload.items() if k in ("sub", "org_id", "role", "permissions")}
    access_token = create_access_token(token_data)

    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=jwt_settings.access_token_expire_minutes,
    )

    return {
        "token": access_token,
        "expires_at": expires_at.isoformat(),
    }


def get_user_info(token_payload: dict) -> dict:
    return {
        "id": token_payload.get("sub", ""),
        "name": "",
        "role": token_payload.get("role", "user"),
        "org_id": token_payload.get("org_id", ""),
        "permissions": token_payload.get("permissions", []),
    }
