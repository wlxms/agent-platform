"""Audit logging — write request audit entries to the audit_logs table."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from agentp_shared.models import AuditLog


async def write_audit_log(
    db: AsyncSession, *, method: str, path: str, status_code: int, latency_ms: int,
    source_ip: str, org_id: str, request_id: str = "", user_id: str = "",
) -> dict:
    log = AuditLog(
        org_id=org_id,
        user_id=user_id or None,
        action=f"{method} {path}",
        resource_type="",
        resource_id=None,
        path=path,
        request_id=request_id or None,
        status_code=status_code,
        ip_address=source_ip,
        request_body={"latency_ms": latency_ms},
    )
    db.add(log)
    await db.commit()
    return {"id": log.id, "timestamp": log.timestamp.isoformat() if log.timestamp else None}
