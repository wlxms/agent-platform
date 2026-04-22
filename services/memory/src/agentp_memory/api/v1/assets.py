"""Internal API routes for Memory assets."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, Response

from agentp_shared.db import get_db
from agentp_shared.errors import OHError
from agentp_shared.responses import ok_response, data_response
from sqlalchemy.ext.asyncio import AsyncSession

from agentp_memory import service
from agentp_memory.schemas import CreateAssetRequest

router = APIRouter()


def _error_json(exc: service.MemoryError) -> tuple[dict, int]:
    return {"code": exc.code, "message": exc.message, "details": {}}, exc.status_code


@router.get("/internal/memory/assets")
async def list_assets(
    path: str | None = Query(default=None, description="Filter by path prefix"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    result = await service.list_assets(
        db, path_prefix=path, page=page, page_size=page_size,
    )
    return result


@router.get("/internal/memory/tree")
async def tree_assets(
    path: str | None = Query(default=None, description="Filter by path prefix"),
    recursive: bool = Query(default=True),
    db: AsyncSession = Depends(get_db),
):
    result = await service.browse_tree(db, path_prefix=path, recursive=recursive)
    return data_response(result)


@router.get("/internal/memory/search")
async def search_assets_route(
    keyword: str = Query(..., min_length=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    result = await service.search_assets(db, keyword=keyword, page=page, page_size=page_size)
    return result


@router.put("/internal/memory/assets/{asset_path:path}")
async def upload_asset(asset_path: str, request: Request, db: AsyncSession = Depends(get_db)):
    content_type = request.headers.get("content-type", "application/octet-stream")
    body = await request.body()
    try:
        result = await service.upload_binary_asset(
            db, path=asset_path, content=body, content_type=content_type,
        )
    except service.MemoryError as exc:
        body, status = _error_json(exc)
        return JSONResponse(content=body, status_code=status)
    return ok_response()


@router.get("/internal/memory/assets/{asset_path:path}/download")
async def download_asset(asset_path: str, db: AsyncSession = Depends(get_db)):
    result = await service.download_binary_asset(db, path=asset_path)
    if result is None:
        from agentp_shared.errors import error_response
        return JSONResponse(status_code=404, content=error_response("NOT_FOUND", "Asset not found"))
    return Response(content=result["content"], media_type=result["content_type"])


@router.get("/internal/memory/assets/{asset_path:path}")
async def get_asset(asset_path: str, db: AsyncSession = Depends(get_db)):
    asset = await service.get_asset(db, path=asset_path)
    if asset is None:
        err = OHError(code="NOT_FOUND", message=f"Asset not found: {asset_path}")
        from fastapi.responses import JSONResponse
        body = {"code": err["detail"]["code"], "message": err["detail"]["message"], "details": err["detail"]["details"]}
        return JSONResponse(content=body, status_code=err["status_code"])
    return {"data": asset}


@router.post("/internal/memory/assets")
async def create_asset(req: CreateAssetRequest, db: AsyncSession = Depends(get_db)):
    try:
        result = await service.create_asset(
            db, path=req.path, content=req.content, content_type=req.content_type,
        )
    except service.MemoryError as exc:
        from fastapi.responses import JSONResponse
        body, status = _error_json(exc)
        return JSONResponse(content=body, status_code=status)
    return {"data": result}


@router.delete("/internal/memory/assets/{asset_path:path}")
async def delete_asset(asset_path: str, db: AsyncSession = Depends(get_db)):
    deleted = await service.delete_asset(db, path=asset_path)
    if not deleted:
        err = OHError(code="NOT_FOUND", message=f"Asset not found: {asset_path}")
        from fastapi.responses import JSONResponse
        body = {"code": err["detail"]["code"], "message": err["detail"]["message"], "details": err["detail"]["details"]}
        return JSONResponse(content=body, status_code=err["status_code"])
    return {"ok": True}
