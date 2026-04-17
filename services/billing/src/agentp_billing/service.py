"""Billing service layer: usage records stored in PostgreSQL, cost calculation, summary aggregation."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agentp_shared.models import UsageRecord, AgentInstance, User, Organization


class BillingError(Exception):
    """Business-level error for billing operations."""
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _calc_cost(input_tokens: int, output_tokens: int) -> float:
    return round(input_tokens * 0.00001 + output_tokens * 0.00003, 6)


# ---- CRUD ----

async def create_usage_record(
    db: AsyncSession,
    *,
    instance_id: str,
    org_id: str,
    user_id: str,
    model: str = "",
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> dict:
    """Insert a usage record and return it as a dict."""
    total_tokens = input_tokens + output_tokens
    cost = _calc_cost(input_tokens, output_tokens)
    rec = UsageRecord(
        instance_id=instance_id,
        org_id=org_id,
        user_id=user_id,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        cost=cost,
    )
    db.add(rec)
    await db.flush()
    return _record_to_dict(rec)


async def get_summary(
    db: AsyncSession,
    *,
    org_id: str,
    period: str = "month",
) -> dict:
    """Aggregate usage summary for an org."""
    now = datetime.now(timezone.utc)
    if period == "month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        start = now - timedelta(days=30)

    # Base filter: org + time range
    base = (
        select(UsageRecord)
        .where(UsageRecord.org_id == org_id, UsageRecord.timestamp >= start)
    )

    # Total tokens + cost
    agg = (
        select(
            func.coalesce(func.sum(UsageRecord.input_tokens + UsageRecord.output_tokens), 0),
            func.coalesce(func.sum(UsageRecord.cost), 0),
        )
        .where(UsageRecord.org_id == org_id, UsageRecord.timestamp >= start)
    )
    row = (await db.execute(agg)).one()
    total_tokens = int(row[0])
    total_cost = round(float(row[1]), 6)

    # By model
    by_model_q = (
        select(
            UsageRecord.model,
            func.sum(UsageRecord.input_tokens + UsageRecord.output_tokens),
            func.sum(UsageRecord.cost),
        )
        .where(UsageRecord.org_id == org_id, UsageRecord.timestamp >= start)
        .group_by(UsageRecord.model)
    )
    by_model = [
        {"model": r[0], "tokens": int(r[1]), "cost": round(float(r[2]), 6)}
        for r in (await db.execute(by_model_q)).all()
    ]

    # Daily trend
    daily_q = (
        select(
            func.date(UsageRecord.timestamp),
            func.sum(UsageRecord.input_tokens + UsageRecord.output_tokens),
            func.sum(UsageRecord.cost),
        )
        .where(UsageRecord.org_id == org_id, UsageRecord.timestamp >= start)
        .group_by(func.date(UsageRecord.timestamp))
        .order_by(func.date(UsageRecord.timestamp))
    )
    daily_trend = [
        {"date": str(r[0]), "tokens": int(r[1]), "cost": round(float(r[2]), 6)}
        for r in (await db.execute(daily_q)).all()
    ]

    return {
        "total_tokens": total_tokens,
        "total_cost": total_cost,
        "by_model": by_model,
        "daily_trend": daily_trend,
    }


async def list_records(
    db: AsyncSession,
    *,
    org_id: str,
    instance_id: str | None = None,
    model: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """List usage records with filtering and pagination."""
    query = select(UsageRecord).where(UsageRecord.org_id == org_id)

    if instance_id is not None:
        query = query.where(UsageRecord.instance_id == instance_id)
    if model is not None:
        query = query.where(UsageRecord.model == model)
    if start_date is not None:
        query = query.where(func.date(UsageRecord.timestamp) >= start_date)
    if end_date is not None:
        query = query.where(func.date(UsageRecord.timestamp) <= end_date)

    # Count
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Paginate
    query = query.order_by(UsageRecord.timestamp.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(query)).scalars().all()

    return {
        "items": [_record_to_dict(r) for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def seed_default_data(db: AsyncSession) -> None:
    """Seed demo usage records if none exist for org-root."""
    from sqlalchemy import select as sa_select

    count_q = sa_select(func.count()).select_from(
        sa_select(UsageRecord).where(UsageRecord.org_id == "org-root").subquery()
    )
    existing = (await db.execute(count_q)).scalar() or 0
    if existing > 0:
        return

    # Ensure seed org, user, and agent instances exist
    for org_id, org_name in [("org-root", "Root Organization")]:
        r = await db.execute(sa_select(Organization).where(Organization.id == org_id))
        if r.scalar_one_or_none() is None:
            db.add(Organization(id=org_id, name=org_name))

    for uid, uname in [("user-admin", "admin"), ("user-billing-seed", "billing-seed")]:
        r = await db.execute(sa_select(User).where(User.id == uid))
        if r.scalar_one_or_none() is None:
            db.add(User(id=uid, org_id="org-root", username=uname, email=f"{uname}@localhost", role="admin"))

    for iid, iname in [("inst-001", "seed-agent-1"), ("inst-002", "seed-agent-2")]:
        r = await db.execute(sa_select(AgentInstance).where(AgentInstance.id == iid))
        if r.scalar_one_or_none() is None:
            db.add(AgentInstance(
                id=iid, org_id="org-root", user_id="user-billing-seed",
                name=iname, status="running",
            ))

    await db.flush()

    seed_records = [
        ("inst-001", "gpt-4", 1200, 800, "2026-04-15T10:30:00Z"),
        ("inst-002", "gpt-3.5-turbo", 500, 300, "2026-04-14T14:00:00Z"),
        ("inst-001", "gpt-4", 2000, 1500, "2026-04-13T09:15:00Z"),
        ("inst-001", "claude-3", 800, 600, "2026-04-12T11:45:00Z"),
        ("inst-002", "gpt-3.5-turbo", 300, 200, "2026-04-11T16:20:00Z"),
    ]
    for instance_id, model, inp, outp, ts_str in seed_records:
        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        rec = UsageRecord(
            instance_id=instance_id,
            org_id="org-root",
            user_id="user-billing-seed",
            model=model,
            input_tokens=inp,
            output_tokens=outp,
            total_tokens=inp + outp,
            cost=_calc_cost(inp, outp),
            timestamp=ts,
        )
        db.add(rec)
    await db.flush()


def _record_to_dict(rec: UsageRecord) -> dict:
    return {
        "id": rec.id,
        "time": rec.timestamp.isoformat() if rec.timestamp else None,
        "instance_name": rec.instance_id,
        "model": rec.model,
        "input_tokens": rec.input_tokens,
        "output_tokens": rec.output_tokens,
        "cost": float(rec.cost) if rec.cost else 0.0,
    }
