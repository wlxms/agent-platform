"""T5.3 — Lifecycle management tests."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


async def test_get_task_status(db_session):
    from agentp_scheduler.lifecycle import create_task_record, get_task_status

    record = await create_task_record(
        db_session, task_type="create_agent", payload={"name": "test-agent"}
    )
    assert record["status"] == "pending"

    status = await get_task_status(db_session, task_id=record["id"])
    assert status is not None
    assert status["id"] == record["id"]


async def test_update_task_completed(db_session):
    from agentp_scheduler.lifecycle import (
        create_task_record,
        get_task_status,
        update_task_status,
    )

    record = await create_task_record(
        db_session, task_type="destroy_agent", payload={"agent_id": "a1"}
    )
    await db_session.commit()

    result = await update_task_status(
        db_session,
        task_id=record["id"],
        status="completed",
        result={"destroyed": True},
    )
    assert result["status"] == "completed"
