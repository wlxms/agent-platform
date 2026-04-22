"""Auth service: API key auth, JWT tokens, user/org management, token blacklist."""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from agentp_shared.config import jwt_settings
from agentp_shared.models import ApiKey, Organization, User
from agentp_shared.redis import get_redis
from agentp_shared.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class AuthError(Exception):
    """Raised when authentication fails."""

    def __init__(self, code: str, message: str, details: dict | None = None):
        from agentp_shared.errors import ErrorStatusMap

        self.code = code
        self.message = message
        self.details = details or {}
        self.status_code = ErrorStatusMap.MAP.get(code, 500)


# ---------------------------------------------------------------------------
# Backward-compatible stub
# ---------------------------------------------------------------------------

def init_api_keys(keys: dict[str, dict] | None = None):  # pragma: no cover
    """DEPRECATED – kept for backward compatibility. No-op."""
    pass


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _hash_api_key(api_key: str) -> str:
    """SHA-256 hash of an API key for storage."""
    return hashlib.sha256(api_key.encode()).hexdigest()


def _generate_api_key(org_id: str) -> str:
    """Generate a new API key: ``oh-{org_id_prefix}-{random_hex}``."""
    prefix = org_id[:8] if len(org_id) >= 8 else org_id
    random_part = secrets.token_hex(16)
    return f"oh-{prefix}-{random_part}"


def _decode_jti(token: str) -> str | None:
    try:
        payload = decode_token(token)
        return payload.get("jti")
    except Exception:
        return None


# ---------------------------------------------------------------------------
# API Key Authentication
# ---------------------------------------------------------------------------

async def authenticate_api_key(api_key: str, db: AsyncSession) -> dict | None:
    """Look up an API key by its raw value. Returns user/org info or ``None``."""
    key_hash = _hash_api_key(api_key)
    result = await db.execute(
        select(ApiKey, User, Organization)
        .join(User, ApiKey.user_id == User.id)
        .join(Organization, User.org_id == Organization.id)
        .where(ApiKey.key_hash == key_hash, ApiKey.status == "active")
    )
    row = result.first()
    if row is None:
        return None

    api_key_obj, user, org = row

    # Check expiration
    if api_key_obj.expires_at and api_key_obj.expires_at < datetime.now(timezone.utc):
        return None

    # Update last_used_at
    await db.execute(
        update(ApiKey)
        .where(ApiKey.id == api_key_obj.id)
        .values(last_used_at=datetime.now(timezone.utc))
    )
    await db.commit()

    return {
        "id": user.id,
        "name": user.username,
        "role": user.role,
        "org_id": user.org_id,
        "org_name": org.name,
        "permissions": api_key_obj.permissions or [],
        "api_key_id": api_key_obj.id,
    }


async def login(api_key: str, db: AsyncSession) -> dict:
    """Authenticate with an API key and return JWT tokens."""
    user_data = await authenticate_api_key(api_key, db)
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

    # Store refresh-token jti in Redis for logout capability
    jti = _decode_jti(refresh_token)
    if jti:
        redis = await get_redis()
        await redis.setex(
            f"agentp:refresh:{jti}",
            jwt_settings.refresh_token_expire_days * 86400,
            user_data["id"],
        )

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


async def refresh(refresh_token_str: str, db: AsyncSession) -> dict:
    """Refresh an access token using a valid refresh token."""
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

    # Check if refresh token has not been revoked
    jti = payload.get("jti")
    if jti:
        redis = await get_redis()
        exists = await redis.exists(f"agentp:refresh:{jti}")
        if not exists:
            raise AuthError(
                code="UNAUTHORIZED", message="Refresh token has been revoked"
            )

    token_data = {
        k: v
        for k, v in payload.items()
        if k in ("sub", "org_id", "role", "permissions")
    }
    access_token = create_access_token(token_data)
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=jwt_settings.access_token_expire_minutes,
    )

    return {
        "token": access_token,
        "expires_at": expires_at.isoformat(),
    }


async def logout(
    refresh_token_str: str | None = None,
    access_token_jti: str | None = None,
) -> None:
    """Revoke tokens. If *refresh_token_str* is given, remove it from Redis."""
    redis = await get_redis()
    if refresh_token_str:
        try:
            payload = decode_token(refresh_token_str)
            jti = payload.get("jti")
            if jti:
                await redis.delete(f"agentp:refresh:{jti}")
        except Exception:
            pass
    if access_token_jti:
        await redis.setex(
            f"agentp:blacklist:{access_token_jti}",
            jwt_settings.access_token_expire_minutes * 60,
            "1",
        )


async def get_user_info(token_payload: dict, db: AsyncSession) -> dict:
    """Get user info from a JWT payload, enriched with DB data."""
    user_id = token_payload.get("sub", "")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    name = user.username if user else ""
    return {
        "id": user_id,
        "name": name,
        "role": token_payload.get("role", "user"),
        "org_id": token_payload.get("org_id", ""),
        "permissions": token_payload.get("permissions", []),
    }


# ---------------------------------------------------------------------------
# Token Blacklist
# ---------------------------------------------------------------------------

async def is_token_blacklisted(jti: str) -> bool:
    redis = await get_redis()
    return await redis.exists(f"agentp:blacklist:{jti}") > 0


# ---------------------------------------------------------------------------
# API Key Management
# ---------------------------------------------------------------------------

async def create_api_key(
    db: AsyncSession,
    org_id: str,
    user_id: str,
    name: str,
    permissions: list[str] | None = None,
    expires_in_days: int | None = None,
) -> dict:
    """Create a new API key. Returns the raw key (only shown once)."""
    if not name or not name.strip():
        raise AuthError(code="VALIDATION_ERROR", message="API key name is required")
    if expires_in_days is not None and expires_in_days < 1:
        raise AuthError(code="VALIDATION_ERROR", message="expires_in_days must be at least 1")

    raw_key = _generate_api_key(org_id)
    key_hash = _hash_api_key(raw_key)
    key_prefix = raw_key[:8]

    expires_at: datetime | None = None
    if expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)

    api_key_obj = ApiKey(
        id=str(uuid.uuid4()),
        org_id=org_id,
        user_id=user_id,
        name=name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        permissions=permissions or [],
        expires_at=expires_at,
        status="active",
    )
    db.add(api_key_obj)
    await db.commit()
    await db.refresh(api_key_obj)

    return {
        "id": api_key_obj.id,
        "api_key": raw_key,
        "name": name,
        "key_prefix": key_prefix,
        "permissions": api_key_obj.permissions,
        "expires_at": (
            api_key_obj.expires_at.isoformat() if api_key_obj.expires_at else None
        ),
        "created_at": (
            api_key_obj.created_at.isoformat() if api_key_obj.created_at else None
        ),
    }


async def list_api_keys(
    db: AsyncSession,
    org_id: str,
    user_id: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """List API keys for an org (optionally filtered by user)."""
    query = select(ApiKey).where(ApiKey.org_id == org_id, ApiKey.status == "active")
    if user_id:
        query = query.where(ApiKey.user_id == user_id)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = (
        query.order_by(ApiKey.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    keys = result.scalars().all()

    return {
        "items": [
            {
                "id": k.id,
                "name": k.name,
                "key_prefix": k.key_prefix,
                "user_id": k.user_id,
                "permissions": k.permissions,
                "expires_at": k.expires_at.isoformat() if k.expires_at else None,
                "last_used_at": (
                    k.last_used_at.isoformat() if k.last_used_at else None
                ),
                "created_at": k.created_at.isoformat() if k.created_at else None,
            }
            for k in keys
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def revoke_api_key(db: AsyncSession, org_id: str, key_id: str) -> dict:
    """Revoke an API key."""
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.org_id == org_id)
    )
    key_obj = result.scalar_one_or_none()
    if key_obj is None:
        raise AuthError(code="NOT_FOUND", message="API key not found")

    key_obj.status = "revoked"
    await db.commit()
    return {"ok": True}


async def renew_api_key(
    db: AsyncSession, org_id: str, key_id: str, expires_in_days: int = 30,
) -> dict:
    """Renew (extend expiration of) an API key."""
    if expires_in_days < 1:
        raise AuthError(code="VALIDATION_ERROR", message="expires_in_days must be at least 1")
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.org_id == org_id, ApiKey.status == "active")
    )
    key_obj = result.scalar_one_or_none()
    if key_obj is None:
        raise AuthError(code="NOT_FOUND", message="API key not found")
    old_expires = key_obj.expires_at
    new_expires = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
    key_obj.expires_at = new_expires
    await db.commit()
    return {
        "ok": True,
        "key_id": key_obj.id,
        "expires_at": new_expires.isoformat(),
        "old_expires_at": old_expires.isoformat() if old_expires else None,
    }


# ---------------------------------------------------------------------------
# Organization Management
# ---------------------------------------------------------------------------

async def create_organization(
    db: AsyncSession,
    name: str,
    parent_id: str | None = None,
    plan: str = "free",
) -> dict:
    """Create a sub-organization."""
    if not name or not name.strip():
        raise AuthError(code="VALIDATION_ERROR", message="Organization name is required")

    org = Organization(
        id=str(uuid.uuid4()), name=name, parent_id=parent_id, plan=plan
    )
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return {
        "id": org.id,
        "name": org.name,
        "parent_id": org.parent_id,
        "plan": org.plan,
    }


async def get_organization(db: AsyncSession, org_id: str) -> dict | None:
    """Get organization details."""
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if org is None:
        return None
    return {
        "id": org.id,
        "name": org.name,
        "parent_id": org.parent_id,
        "level": org.level,
        "plan": org.plan,
        "status": org.status,
    }


async def get_org_tree(
    db: AsyncSession, org_id: str | None = None, depth: int = 3
) -> dict | None:
    """Get organization tree. If *org_id* is ``None``, get root orgs."""
    if org_id:
        result = await db.execute(
            select(Organization).where(Organization.id == org_id)
        )
        root = result.scalar_one_or_none()
        if root is None:
            return None
        return await _build_org_tree(db, root, depth)
    else:
        result = await db.execute(
            select(Organization).where(Organization.parent_id.is_(None))
        )
        roots = result.scalars().all()
        return {
            "children": [await _build_org_tree(db, r, depth) for r in roots]
        }


async def _build_org_tree(
    db: AsyncSession, org: Organization, remaining_depth: int
) -> dict:
    node: dict = {"id": org.id, "name": org.name, "plan": org.plan}
    if remaining_depth > 1:
        result = await db.execute(
            select(Organization).where(Organization.parent_id == org.id)
        )
        children = result.scalars().all()
        node["children"] = [
            await _build_org_tree(db, c, remaining_depth - 1) for c in children
        ]
    else:
        node["children"] = []
    return node


# ---------------------------------------------------------------------------
# User Management
# ---------------------------------------------------------------------------

async def create_user(
    db: AsyncSession,
    org_id: str,
    username: str,
    email: str,
    role: str = "member",
) -> dict:
    """Create a user in an organization."""
    user = User(
        id=str(uuid.uuid4()),
        org_id=org_id,
        username=username,
        email=email,
        role=role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return {
        "id": user.id,
        "org_id": user.org_id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
    }


async def list_org_members(
    db: AsyncSession,
    org_id: str,
    page: int = 1,
    page_size: int = 20,
    role: str | None = None,
) -> dict:
    """List members of an organization."""
    query = select(User).where(User.org_id == org_id, User.status == "active")
    if role:
        query = query.where(User.role == role)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = (
        query.order_by(User.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    users = result.scalars().all()

    return {
        "items": [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "role": u.role,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# ---------------------------------------------------------------------------
# Org Member Management
# ---------------------------------------------------------------------------

VALID_ROLES = {"admin", "manager", "member"}


async def add_org_member(
    db: AsyncSession, org_id: str, user_id: str, role: str = "member",
) -> dict:
    if role not in VALID_ROLES:
        raise AuthError(code="VALIDATION_ERROR", message=f"Invalid role: {role}. Must be one of {VALID_ROLES}")
    result = await db.execute(select(User).where(User.id == user_id, User.org_id == org_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise AuthError(code="NOT_FOUND", message="User not found in organization")
    user.role = role
    user.status = "active"
    await db.commit()
    return {"org_id": user.org_id, "user_id": user.id, "role": user.role, "username": user.username}


async def remove_org_member(db: AsyncSession, org_id: str, user_id: str) -> dict:
    result = await db.execute(select(User).where(User.id == user_id, User.org_id == org_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise AuthError(code="NOT_FOUND", message="User not found in organization")
    user.status = "removed"
    await db.commit()
    return {"ok": True}


async def update_member_role(db: AsyncSession, org_id: str, user_id: str, role: str) -> dict:
    if role not in VALID_ROLES:
        raise AuthError(code="VALIDATION_ERROR", message=f"Invalid role: {role}. Must be one of {VALID_ROLES}")
    result = await db.execute(select(User).where(User.id == user_id, User.org_id == org_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise AuthError(code="NOT_FOUND", message="User not found in organization")
    user.role = role
    await db.commit()
    return {"ok": True, "user_id": user.id, "role": role}


# ---------------------------------------------------------------------------
# Permissions & Roles
# ---------------------------------------------------------------------------

PERMISSION_DESCRIPTIONS = {
    "agents:create": "Create agent instances",
    "agents:read": "View agent instances",
    "agents:destroy": "Delete agent instances",
    "agents:manage": "Full agent lifecycle management",
    "members:read": "View organization members",
    "members:manage": "Add, remove, or update members",
    "billing:read": "View billing information",
    "billing:manage": "Modify billing rules",
    "configs:manage": "Create and modify agent configs",
    "approvals:read": "View approval requests",
    "approvals:manage": "Review and decide on approvals",
    "org:manage": "Organization settings management",
    "permissions:read": "View permission and role definitions",
    "roles:manage": "Assign and modify user roles",
}


def get_permissions() -> list[dict]:
    from agentp_shared.security import ALL_PERMISSIONS
    return [
        {
            "id": perm,
            "description": PERMISSION_DESCRIPTIONS.get(perm, ""),
        }
        for perm in ALL_PERMISSIONS
    ]


def get_roles() -> list[dict]:
    from agentp_shared.security import ROLE_PERMISSIONS
    return [
        {
            "name": role,
            "permissions": perms,
        }
        for role, perms in ROLE_PERMISSIONS.items()
    ]


# ---------------------------------------------------------------------------
# Seed Data
# ---------------------------------------------------------------------------

async def seed_default_data(db: AsyncSession) -> None:
    """Create default root org, admin user, and admin API key if they don't exist."""
    # Check if root org already exists
    result = await db.execute(
        select(Organization).where(Organization.name == "Root")
    )
    if result.scalar_one_or_none() is not None:
        return

    # Root org
    root_org = Organization(
        id="org-root", name="Root", level=1, plan="enterprise"
    )
    db.add(root_org)
    await db.flush()

    # Admin user
    admin_user = User(
        id="user-admin",
        org_id="org-root",
        username="admin",
        email="admin@localhost",
        role="admin",
    )
    db.add(admin_user)
    await db.flush()

    # Admin API key
    admin_key_raw = "oh-admin-key-default"
    admin_key = ApiKey(
        id="key-admin-default",
        org_id="org-root",
        user_id="user-admin",
        name="Default Admin Key",
        key_hash=_hash_api_key(admin_key_raw),
        key_prefix=admin_key_raw[:8],
        permissions=["*"],
        status="active",
    )
    db.add(admin_key)

    # Demo org + user
    demo_org = Organization(
        id="org-demo", name="Demo", parent_id="org-root", level=2, plan="basic"
    )
    db.add(demo_org)
    await db.flush()

    demo_user = User(
        id="user-demo",
        org_id="org-demo",
        username="demo",
        email="demo@localhost",
        role="member",
    )
    db.add(demo_user)
    await db.flush()

    demo_key_raw = "oh-demo-key-default"
    demo_key = ApiKey(
        id="key-demo-default",
        org_id="org-demo",
        user_id="user-demo",
        name="Default Demo Key",
        key_hash=_hash_api_key(demo_key_raw),
        key_prefix=demo_key_raw[:8],
        permissions=["agent:manage"],
        status="active",
    )
    db.add(demo_key)

    await db.commit()
