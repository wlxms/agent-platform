"""Internal API routes for Market service."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from agentp_shared.db import get_db
from agentp_shared.errors import OHError
from agentp_market.service import (
    create_template, get_template, list_templates,
    list_skills, list_mcp_servers,
    create_category, list_categories,
    create_config, get_config, update_config, delete_config,
    list_configs, publish_config, duplicate_config,
    get_config_versions, validate_config, validate_config_full,
    MarketError,
)
from agentp_shared.responses import data_response

router = APIRouter()


# ------------------------------------------------------------------
# Templates
# ------------------------------------------------------------------

@router.get("/internal/market/templates")
async def list_templates_route(
    category: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await list_templates(db, category=category, keyword=keyword, page=page, page_size=page_size)


@router.get("/internal/market/templates/{template_id}")
async def get_template_route(template_id: str, db: AsyncSession = Depends(get_db)):
    tpl = await get_template(db, template_id=template_id)
    if tpl is None:
        err = OHError(code="NOT_FOUND", message=f"Template not found: {template_id}")
        raise HTTPException(status_code=err["status_code"], detail=err["detail"])
    return {"data": tpl}


# ------------------------------------------------------------------
# Skills
# ------------------------------------------------------------------

@router.get("/internal/market/skills")
async def list_skills_route(
    keyword: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await list_skills(db, keyword=keyword, page=page, page_size=page_size)


# ------------------------------------------------------------------
# MCP servers
# ------------------------------------------------------------------

@router.get("/internal/market/mcps")
async def list_mcps_route(
    keyword: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await list_mcp_servers(db, keyword=keyword, page=page, page_size=page_size)


# ------------------------------------------------------------------
# Categories
# ------------------------------------------------------------------

@router.get("/internal/market/categories")
async def list_categories_route(db: AsyncSession = Depends(get_db)):
    return await list_categories(db)


@router.post("/internal/market/categories")
async def create_category_route(
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    result = await create_category(db, **body)
    return {"data": result}


# ------------------------------------------------------------------
# Builder Router (11 endpoints)
# ------------------------------------------------------------------

builder_router = APIRouter()


@builder_router.get("/internal/market/configs")
async def list_configs_route(
    org_id: str = Query(default=""),
    visibility: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await list_configs(db, org_id=org_id, visibility=visibility,
                              keyword=keyword, page=page, page_size=page_size)


@builder_router.get("/internal/market/configs/{config_id}")
async def get_config_route(config_id: str, db: AsyncSession = Depends(get_db)):
    result = await get_config(db, config_id=config_id)
    if result is None:
        err = OHError(code="NOT_FOUND", message=f"Config not found: {config_id}")
        raise HTTPException(status_code=err["status_code"], detail=err["detail"])
    return data_response(result)


@builder_router.post("/internal/market/configs")
async def create_config_route(config: dict, db: AsyncSession = Depends(get_db)):
    result = await create_config(db, **config)
    return data_response(result)


@builder_router.put("/internal/market/configs/{config_id}")
async def update_config_route(config_id: str, config: dict, db: AsyncSession = Depends(get_db)):
    try:
        result = await update_config(db, config_id=config_id, **config)
        return data_response(result)
    except MarketError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message})


@builder_router.delete("/internal/market/configs/{config_id}")
async def delete_config_route(config_id: str, db: AsyncSession = Depends(get_db)):
    try:
        result = await delete_config(db, config_id=config_id)
        return data_response(result)
    except MarketError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message})


@builder_router.post("/internal/market/configs/{config_id}/publish")
async def publish_config_route(config_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    try:
        result = await publish_config(db, config_id=config_id, **body)
        return data_response(result)
    except MarketError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message})


@builder_router.post("/internal/market/configs/{config_id}/duplicate")
async def duplicate_config_route(config_id: str, body: dict, db: AsyncSession = Depends(get_db)):
    try:
        result = await duplicate_config(db, config_id=config_id, name=body.get("name", ""))
        return data_response(result)
    except MarketError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message})


@builder_router.get("/internal/market/configs/{config_id}/versions")
async def list_versions_route(config_id: str, page: int = Query(default=1, ge=1),
                              page_size: int = Query(default=20, ge=1, le=100),
                              db: AsyncSession = Depends(get_db)):
    return await get_config_versions(db, config_id=config_id, page=page, page_size=page_size)


@builder_router.post("/internal/market/configs/validate")
async def validate_config_route(config: dict):
    result = validate_config_full(config)
    return data_response(result)


@builder_router.get("/internal/market/configs/{config_id}/export")
async def export_config_route(config_id: str, format: str = Query(default="json", pattern="^(json|yaml)$"),
                              db: AsyncSession = Depends(get_db)):
    from agentp_market.service import export_config as export_fn
    config = await get_config(db, config_id=config_id)
    if config is None:
        err = OHError(code="NOT_FOUND", message=f"Config not found: {config_id}")
        raise HTTPException(status_code=err["status_code"], detail=err["detail"])
    content = export_fn(config, format=format)
    media = "application/yaml" if format == "yaml" else "application/json"
    from fastapi.responses import Response as FastAPIResponse
    return FastAPIResponse(content=content, media_type=media)


@builder_router.post("/internal/market/configs/import")
async def import_config_route(body: dict, db: AsyncSession = Depends(get_db)):
    from agentp_market.service import import_config as import_fn
    data = import_fn(body.get("content", ""), source=body.get("source", "json"))
    org_id = body.get("org_id", "")
    author_id = body.get("author_id", "")
    if not org_id or not author_id:
        raise HTTPException(status_code=422, detail={"code": "VALIDATION_ERROR", "message": "org_id and author_id are required"})
    result = await create_config(db, org_id=org_id, author_id=author_id, **data)
    return data_response(result)
