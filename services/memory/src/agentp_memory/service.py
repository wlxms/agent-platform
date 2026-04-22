"""Memory service — PostgreSQL-backed asset storage."""
from __future__ import annotations

import base64
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, delete, func, cast, String
from sqlalchemy.ext.asyncio import AsyncSession

from agentp_shared.models import MemoryAsset

_utcnow = lambda: datetime.now(timezone.utc)

DEFAULT_ORG_ID = "org-root"


class MemoryError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


# ------------------------------------------------------------------
# CRUD
# ------------------------------------------------------------------

async def create_asset(
    db: AsyncSession,
    *,
    path: str,
    content: str = "",
    content_type: str = "text/plain",
    org_id: str = DEFAULT_ORG_ID,
) -> dict:
    if not path or not path.strip():
        raise MemoryError(code="VALIDATION_ERROR", message="Asset path is required")

    path = path.strip()

    # Upsert: find existing
    result = await db.execute(
        select(MemoryAsset).where(MemoryAsset.org_id == org_id, MemoryAsset.path == path)
    )
    existing = result.scalar_one_or_none()

    now = _utcnow()
    if existing is not None:
        existing.content_type = content_type
        existing.size_bytes = len(content.encode("utf-8")) if content else 0
        existing.storage_ref = ""
        existing.metadata_ = {"content": content}
        existing.updated_at = now
        await db.flush()
        return _asset_to_dict(existing)
    else:
        asset = MemoryAsset(
            id=str(uuid.uuid4()),
            org_id=org_id,
            path=path,
            content_type=content_type,
            size_bytes=len(content.encode("utf-8")) if content else 0,
            storage_ref="",
            metadata_={"content": content},
            created_at=now,
            updated_at=now,
        )
        db.add(asset)
        await db.flush()
        return _asset_to_dict(asset)


async def get_asset(
    db: AsyncSession,
    *,
    path: str,
    org_id: str = DEFAULT_ORG_ID,
) -> dict | None:
    result = await db.execute(
        select(MemoryAsset).where(MemoryAsset.org_id == org_id, MemoryAsset.path == path)
    )
    asset = result.scalar_one_or_none()
    if asset is None:
        return None
    return _asset_to_dict(asset)


async def list_assets(
    db: AsyncSession,
    *,
    path_prefix: str | None = None,
    org_id: str = DEFAULT_ORG_ID,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    q = select(MemoryAsset).where(MemoryAsset.org_id == org_id)
    count_q = select(func.count()).select_from(MemoryAsset).where(MemoryAsset.org_id == org_id)

    if path_prefix:
        q = q.where(MemoryAsset.path.startswith(path_prefix))
        count_q = count_q.where(MemoryAsset.path.startswith(path_prefix))

    # Total count
    total_result = await db.execute(count_q)
    total = total_result.scalar() or 0

    # Pagination
    offset = (page - 1) * page_size
    q = q.order_by(MemoryAsset.path).offset(offset).limit(page_size)

    result = await db.execute(q)
    assets = result.scalars().all()

    items = [_asset_to_summary(a) for a in assets]
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def delete_asset(
    db: AsyncSession,
    *,
    path: str,
    org_id: str = DEFAULT_ORG_ID,
) -> bool:
    result = await db.execute(
        delete(MemoryAsset).where(MemoryAsset.org_id == org_id, MemoryAsset.path == path)
    )
    await db.flush()
    return result.rowcount > 0


# ------------------------------------------------------------------
# Binary upload / download
# ------------------------------------------------------------------

async def upload_binary_asset(
    db: AsyncSession,
    *,
    path: str,
    content: bytes,
    content_type: str = "application/octet-stream",
    org_id: str = DEFAULT_ORG_ID,
) -> dict:
    if not path or not path.strip():
        raise MemoryError(code="VALIDATION_ERROR", message="Asset path is required")
    path = path.strip()
    result = await db.execute(
        select(MemoryAsset).where(MemoryAsset.org_id == org_id, MemoryAsset.path == path)
    )
    existing = result.scalar_one_or_none()
    now = _utcnow()
    encoded = base64.b64encode(content).decode("ascii")
    if existing is not None:
        existing.content_type = content_type
        existing.size_bytes = len(content)
        existing.metadata_ = {"binary": True, "content_b64": encoded}
        existing.updated_at = now
        await db.flush()
    else:
        asset = MemoryAsset(
            id=str(uuid.uuid4()),
            org_id=org_id,
            path=path,
            content_type=content_type,
            size_bytes=len(content),
            storage_ref="",
            metadata_={"binary": True, "content_b64": encoded},
            created_at=now,
            updated_at=now,
        )
        db.add(asset)
        await db.flush()
    return {"ok": True, "path": path, "size_bytes": len(content), "content_type": content_type}


async def download_binary_asset(
    db: AsyncSession,
    *,
    path: str,
    org_id: str = DEFAULT_ORG_ID,
) -> dict | None:
    result = await db.execute(
        select(MemoryAsset).where(MemoryAsset.org_id == org_id, MemoryAsset.path == path)
    )
    asset = result.scalar_one_or_none()
    if asset is None:
        return None
    metadata = asset.metadata_ or {}
    if metadata.get("binary"):
        content = base64.b64decode(metadata.get("content_b64", ""))
    else:
        content = (metadata.get("content") or "").encode("utf-8")
    return {"content": content, "content_type": asset.content_type, "size_bytes": asset.size_bytes}


# ------------------------------------------------------------------
# Keyword search
# ------------------------------------------------------------------

async def search_assets(
    db: AsyncSession,
    *,
    keyword: str,
    org_id: str = DEFAULT_ORG_ID,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    if not keyword or not keyword.strip():
        return {"items": [], "total": 0, "page": page, "page_size": page_size}
    q = select(MemoryAsset).where(
        MemoryAsset.org_id == org_id,
        cast(MemoryAsset.metadata_["content"], String).ilike(f"%{keyword}%"),
    )
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    q = q.order_by(MemoryAsset.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(q)).scalars().all()

    items = [_asset_to_dict(r) for r in rows]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


# ------------------------------------------------------------------
# Tree browsing
# ------------------------------------------------------------------

async def browse_tree(
    db: AsyncSession,
    *,
    org_id: str = DEFAULT_ORG_ID,
    path_prefix: str | None = None,
    recursive: bool = True,
) -> dict:
    q = select(MemoryAsset).where(MemoryAsset.org_id == org_id)
    if path_prefix:
        q = q.where(MemoryAsset.path.startswith(path_prefix))
    rows = (await db.execute(q)).scalars().all()

    paths = sorted([a.path for a in rows])
    tree: dict = {}
    for p in paths:
        parts = p.strip("/").split("/")
        current = tree
        for part in parts:
            if part not in current:
                current[part] = {}
            current = current[part]
    return {"paths": paths, "tree": tree}


# ------------------------------------------------------------------
# Seed sample data
# ------------------------------------------------------------------

async def seed_default_data(db: AsyncSession) -> None:
    """Create sample memory assets if they don't exist."""
    sample_assets = [
        ("system/prompt.txt", "You are a helpful assistant.", "text/plain"),
        ("system/config.json", '{"model": "gpt-4"}', "application/json"),
        ("workspace/notes.md", "# Notes\n\nSome notes here.", "text/markdown"),
    ]
    for path, content, content_type in sample_assets:
        await create_asset(
            db, path=path, content=content, content_type=content_type, org_id=DEFAULT_ORG_ID,
        )


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _asset_to_dict(asset: MemoryAsset) -> dict:
    content = asset.metadata_.get("content", "") if isinstance(asset.metadata_, dict) else ""
    return {
        "id": asset.id,
        "path": asset.path,
        "content": content,
        "content_type": asset.content_type,
        "size_bytes": asset.size_bytes,
        "created_at": asset.created_at.isoformat() if asset.created_at else None,
        "updated_at": asset.updated_at.isoformat() if asset.updated_at else None,
    }


def _asset_to_summary(asset: MemoryAsset) -> dict:
    name = asset.path.rsplit("/", 1)[-1] if "/" in asset.path else asset.path
    return {
        "path": asset.path,
        "name": name,
        "type": "file",
        "size": asset.size_bytes,
        "content_type": asset.content_type,
        "updated_at": asset.updated_at.isoformat() if asset.updated_at else None,
    }
