"""T5.2 — Approval workflow tests."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


async def test_create_approval(db_session):
    from agentp_scheduler.approval import create_approval_request, list_approvals
    import uuid
    from agentp_shared.models import Organization
    from sqlalchemy import select

    org_id = f"org-{uuid.uuid4().hex[:8]}"
    db_session.add(Organization(id=org_id, name="Test Approval Org"))
    await db_session.flush()

    result = await create_approval_request(
        db_session,
        org_id=org_id,
        applicant_id="u1",
        template_name="Code Reviewer",
        config_summary={"personality": {"tone": "pro"}},
        reason="Need this",
    )
    assert result["status"] == "pending"

    approvals = await list_approvals(db_session, org_id=org_id, status="pending")
    assert approvals["total"] == 1


async def test_approve_request(db_session):
    from agentp_scheduler.approval import create_approval_request, approve_request
    import uuid

    org_id = f"org-{uuid.uuid4().hex[:8]}"
    # Seed org so FK constraint is satisfied
    from agentp_shared.models import Organization
    from sqlalchemy import select
    existing = (await db_session.execute(
        select(Organization).where(Organization.id == org_id)
    )).scalar_one_or_none()
    if not existing:
        db_session.add(Organization(id=org_id, name="Test Approval Org"))
        await db_session.flush()

    created = await create_approval_request(
        db_session, org_id=org_id, applicant_id="u1", template_name="X", reason="Y"
    )

    result = await approve_request(
        db_session, approval_id=created["id"], reviewer_id="admin-u1"
    )
    assert result["ok"] is True
    assert result["status"] == "approved"


async def test_reject_request(db_session):
    from agentp_scheduler.approval import (
        create_approval_request,
        reject_request,
    )
    import uuid

    org_id = f"org-{uuid.uuid4().hex[:8]}"
    from agentp_shared.models import Organization
    from sqlalchemy import select
    existing = (await db_session.execute(
        select(Organization).where(Organization.id == org_id)
    )).scalar_one_or_none()
    if not existing:
        db_session.add(Organization(id=org_id, name="Test Reject Org"))
        await db_session.flush()

    created = await create_approval_request(
        db_session, org_id=org_id, applicant_id="u1", template_name="X", reason="Y"
    )

    result = await reject_request(
        db_session, approval_id=created["id"], reviewer_id="admin-u1"
    )
    assert result["status"] == "rejected"
