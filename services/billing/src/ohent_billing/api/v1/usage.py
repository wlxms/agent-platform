"""Billing API v1 endpoints: usage summary and records."""
from __future__ import annotations

from fastapi import APIRouter, Query

from ohent_shared.responses import data_response, list_response

from ... import service

router = APIRouter(prefix="/internal/billing/usage", tags=["billing"])


@router.get("/summary")
async def summary(period: str = Query(default="month")):
    svc = service.get_billing_service()
    result = svc.get_summary(period=period)
    return data_response(result)


@router.get("/records")
async def records(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    instance_id: str | None = Query(default=None),
    model: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
):
    svc = service.get_billing_service()
    result = svc.list_records(
        instance_id=instance_id,
        model=model,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )
    return list_response(
        items=result["items"],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )
