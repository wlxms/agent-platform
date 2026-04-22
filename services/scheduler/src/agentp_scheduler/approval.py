"""T5.2 — Approval workflow: create, list, approve, reject."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from agentp_shared.models import Approval
from agentp_shared.responses import list_response, ok_response

_utcnow = lambda: datetime.now(timezone.utc)


class ApprovalError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


async def create_approval_request(
    db: AsyncSession,
    *,
    org_id: str,
    applicant_id: str,
    template_name: str = "",
    config_summary: dict[str, Any] | None = None,
    reason: str = "",
) -> dict[str, Any]:
    approval = Approval(
        id=str(uuid.uuid4()),
        org_id=org_id,
        applicant_id=applicant_id,
        status="pending",
        template_name=template_name,
        config_snapshot=config_summary or {},
        review_comment=reason,
    )
    db.add(approval)
    await db.flush()
    return _approval_to_dict(approval)


async def list_approvals(
    db: AsyncSession,
    *,
    org_id: str,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    q = select(Approval).where(Approval.org_id == org_id)
    if status:
        q = q.where(Approval.status == status)

    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    q = q.order_by(Approval.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(q)).scalars().all()
    return list_response([_approval_to_dict(r) for r in rows], total, page, page_size)


async def approve_request(
    db: AsyncSession, *, approval_id: str, reviewer_id: str
) -> dict[str, Any]:
    result = await db.execute(select(Approval).where(Approval.id == approval_id))
    approval = result.scalar_one_or_none()
    if not approval:
        raise ApprovalError("NOT_FOUND", f"Approval {approval_id} not found", 404)
    if approval.status != "pending":
        raise ApprovalError(
            "CONFLICT", f"Approval is already {approval.status}", 409
        )
    approval.status = "approved"
    approval.reviewer_id = reviewer_id
    approval.reviewed_at = _utcnow()
    await db.flush()
    return {"ok": True, "status": "approved", "task_id": approval.id}


async def reject_request(
    db: AsyncSession,
    *,
    approval_id: str,
    reviewer_id: str,
    reason: str = "",
) -> dict[str, Any]:
    result = await db.execute(select(Approval).where(Approval.id == approval_id))
    approval = result.scalar_one_or_none()
    if not approval:
        raise ApprovalError("NOT_FOUND", f"Approval {approval_id} not found", 404)
    if approval.status != "pending":
        raise ApprovalError(
            "CONFLICT", f"Approval is already {approval.status}", 409
        )
    approval.status = "rejected"
    approval.reviewer_id = reviewer_id
    approval.review_comment = reason or approval.review_comment
    approval.reviewed_at = _utcnow()
    await db.flush()
    return {"ok": True, "status": "rejected"}


def _approval_to_dict(a: Approval) -> dict[str, Any]:
    return {
        "id": a.id,
        "org_id": a.org_id,
        "applicant_id": a.applicant_id,
        "status": a.status,
        "template_name": a.template_name,
        "config_summary": a.config_snapshot,
        "reason": a.review_comment,
        "reviewed_by": a.reviewer_id,
        "reviewed_at": a.reviewed_at.isoformat() if a.reviewed_at else None,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }
