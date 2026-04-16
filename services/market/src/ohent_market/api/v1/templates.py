"""Internal API routes for Market service."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ohent_market.service import MarketService
from ohent_shared.errors import OHError

router = APIRouter()

_service: MarketService | None = None


def get_service() -> MarketService:
    global _service
    if _service is None:
        _service = MarketService()
    return _service


def reset_service() -> None:
    global _service
    _service = None


# ------------------------------------------------------------------
# Templates
# ------------------------------------------------------------------

@router.get("/internal/market/templates")
async def list_templates(
    category: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    svc = get_service()
    return svc.list_templates(category=category, keyword=keyword, page=page, page_size=page_size)


@router.get("/internal/market/templates/{template_id}")
async def get_template(template_id: str):
    svc = get_service()
    tpl = svc.get_template(template_id)
    if tpl is None:
        err = OHError(code="NOT_FOUND", message=f"Template not found: {template_id}")
        raise HTTPException(status_code=err["status_code"], detail=err["detail"])
    return {"data": tpl}


# ------------------------------------------------------------------
# Skills
# ------------------------------------------------------------------

@router.get("/internal/market/skills")
async def list_skills(
    keyword: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    svc = get_service()
    return svc.list_skills(keyword=keyword, page=page, page_size=page_size)


# ------------------------------------------------------------------
# MCP servers
# ------------------------------------------------------------------

@router.get("/internal/market/mcps")
async def list_mcps(
    keyword: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    svc = get_service()
    return svc.list_mcps(keyword=keyword, page=page, page_size=page_size)
