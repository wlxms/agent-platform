"""T5.3 — Agent lifecycle management: task record CRUD."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentp_shared.models import TaskRecord

_utcnow = lambda: datetime.now(timezone.utc)


async def create_task_record(
    db: AsyncSession,
    *,
    task_type: str,
    payload: dict[str, Any] | None = None,
    priority: int = 0,
) -> dict[str, Any]:
    record = TaskRecord(
        id=str(uuid.uuid4()),
        type=task_type,
        status="pending",
        payload=payload or {},
        priority=priority,
    )
    db.add(record)
    await db.flush()
    return {
        "id": record.id,
        "type": record.type,
        "status": record.status,
        "payload": record.payload,
    }


async def get_task_status(
    db: AsyncSession, *, task_id: str
) -> dict[str, Any] | None:
    result = await db.execute(select(TaskRecord).where(TaskRecord.id == task_id))
    rec = result.scalar_one_or_none()
    if not rec:
        return None
    return {
        "id": rec.id,
        "type": rec.type,
        "status": rec.status,
        "payload": rec.payload,
        "result": rec.result,
        "error_message": rec.error_message,
        "priority": rec.priority,
        "retry_count": rec.retry_count,
        "scheduled_at": rec.scheduled_at.isoformat() if rec.scheduled_at else None,
        "started_at": rec.started_at.isoformat() if rec.started_at else None,
        "completed_at": rec.completed_at.isoformat() if rec.completed_at else None,
        "created_at": rec.created_at.isoformat() if rec.created_at else None,
    }


async def update_task_status(
    db: AsyncSession,
    *,
    task_id: str,
    status: str,
    result: dict[str, Any] | None = None,
    error_message: str | None = None,
) -> dict[str, Any]:
    result_row = await db.execute(
        select(TaskRecord).where(TaskRecord.id == task_id)
    )
    rec = result_row.scalar_one_or_none()
    if not rec:
        return {"error": "not_found", "task_id": task_id}
    rec.status = status
    if result is not None:
        rec.result = result
    if error_message is not None:
        rec.error_message = error_message
    if status == "running":
        rec.started_at = _utcnow()
    elif status in ("completed", "failed"):
        rec.completed_at = _utcnow()
    await db.flush()
    return {"id": rec.id, "status": rec.status}
