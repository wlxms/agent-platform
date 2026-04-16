"""Internal API routes for Memory assets."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ohent_memory.service import MemoryService
from ohent_memory.schemas import CreateAssetRequest
from ohent_shared.errors import OHError

router = APIRouter()

_service: MemoryService | None = None


def get_service() -> MemoryService:
    global _service
    if _service is None:
        _service = MemoryService()
    return _service


@router.get("/internal/memory/assets")
async def list_assets(
    path: str | None = Query(default=None, description="Filter by path prefix"),
):
    svc = get_service()
    items = svc.list_assets(path_prefix=path)
    return {"items": items, "total": len(items), "page": 1, "page_size": len(items)}


@router.get("/internal/memory/assets/{asset_path:path}")
async def get_asset(asset_path: str):
    svc = get_service()
    asset = svc.get_asset(asset_path)
    if asset is None:
        err = OHError(code="NOT_FOUND", message=f"Asset not found: {asset_path}")
        raise HTTPException(status_code=err["status_code"], detail=err["detail"])
    return {"data": asset}


@router.post("/internal/memory/assets")
async def create_asset(req: CreateAssetRequest):
    svc = get_service()
    result = svc.create_asset(path=req.path, content=req.content, content_type=req.content_type)
    return {"data": result}


@router.delete("/internal/memory/assets/{asset_path:path}")
async def delete_asset(asset_path: str):
    svc = get_service()
    deleted = svc.delete_asset(asset_path)
    if not deleted:
        err = OHError(code="NOT_FOUND", message=f"Asset not found: {asset_path}")
        raise HTTPException(status_code=err["status_code"], detail=err["detail"])
    return {"ok": True}
