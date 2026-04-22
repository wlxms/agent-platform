"""Billing API v1 — budget, rules, export, org-summary routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from agentp_shared.db import get_db
from agentp_shared.responses import ok_response, data_response, list_response
from agentp_shared.schemas import BudgetUpdate as BudgetUpdateRequest

from ... import service

router = APIRouter(tags=["billing"])

DEFAULT_ORG_ID = "org-root"


def _get_org_id_from_token(request: Request) -> str:
    from agentp_shared.security import decode_token
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        return "org-root"
    try:
        payload = decode_token(auth[7:])
        return payload.get("org_id", "org-root")
    except Exception:
        return "org-root"


@router.get("/internal/billing/budget")
async def get_budget_route(request: Request, org_id: str | None = Query(default=None), db: AsyncSession = Depends(get_db)):
    if not org_id:
        org_id = _get_org_id_from_token(request)
    budget = await service.get_budget(db, org_id=org_id)
    if budget is None:
        return data_response({"threshold": 0, "alert_rules": {}})
    return data_response(budget)


@router.put("/internal/billing/budget")
async def update_budget_route(req: BudgetUpdateRequest, request: Request, db: AsyncSession = Depends(get_db)):
    org_id = _get_org_id_from_token(request)
    await service.set_budget(db, org_id=org_id, threshold=req.threshold or 0, alert_rules=req.alert_rules)
    return ok_response()


@router.get("/internal/billing/export")
async def export_billing(request: Request, start_date: str | None = Query(default=None), end_date: str | None = Query(default=None), format: str = Query(default="csv"), db: AsyncSession = Depends(get_db)):
    org_id = _get_org_id_from_token(request)
    records = await service.get_records_for_export(db, org_id=org_id, start_date=start_date, end_date=end_date)
    if format == "csv":
        csv_content = service.export_records_csv(records)
        from fastapi.responses import Response
        return Response(content=csv_content, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=billing_export.csv"})
    return data_response(records)


@router.post("/internal/billing/rules")
async def create_rule(req: dict, db: AsyncSession = Depends(get_db)):
    rule = await service.create_billing_rule(db, **req)
    return data_response(rule)


@router.get("/internal/billing/rules")
async def list_rules(page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100), db: AsyncSession = Depends(get_db)):
    result = await service.list_billing_rules(db, org_id=DEFAULT_ORG_ID, page=page, page_size=page_size)
    return list_response(items=result["items"], total=result["total"], page=result["page"], page_size=result["page_size"])


@router.put("/internal/billing/rules/{rule_id}")
async def update_rule(rule_id: str, req: dict, db: AsyncSession = Depends(get_db)):
    result = await service.update_billing_rule(db, rule_id=rule_id, **req)
    return data_response(result)


@router.delete("/internal/billing/rules/{rule_id}")
async def delete_rule(rule_id: str, db: AsyncSession = Depends(get_db)):
    result = await service.delete_billing_rule(db, rule_id=rule_id)
    return data_response(result)


@router.get("/internal/billing/org-summary")
async def org_summary_route(request: Request, period: str = Query(default="month"), org_id: str | None = Query(default=None), db: AsyncSession = Depends(get_db)):
    if not org_id:
        org_id = _get_org_id_from_token(request)
    result = await service.get_org_summary(db, org_id=org_id, period=period)
    return data_response(result)
