"""Tests for audit logging middleware (T6.3)."""
import pytest


@pytest.mark.asyncio
async def test_audit_log_created(db_session):
    from agentp_gateway.audit import write_audit_log
    log = await write_audit_log(
        db_session,
        method="POST",
        path="/api/v1/agents",
        status_code=201,
        latency_ms=42,
        source_ip="127.0.0.1",
        org_id="org-root",
        request_id="req-1",
    )
    assert log["id"] is not None
    from sqlalchemy import select
    from agentp_shared.models import AuditLog
    result = await db_session.execute(select(AuditLog))
    records = result.scalars().all()
    assert len(records) >= 1
