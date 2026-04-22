"""T5.4 — Celery app and async task definitions for the scheduler."""
from __future__ import annotations

from celery import Celery

from agentp_shared.config import redis_settings

celery = Celery(
    "agentp_scheduler",
    broker=f"redis://{redis_settings.url}",
    backend=f"redis://{redis_settings.url}",
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
)


@celery.task(
    name="scheduler.process_approval",
    bind=True,
    max_retries=3,
)
def process_approval_task(
    self,
    approval_id: str,
    action: str,
    reviewer_id: str,
    reason: str = "",
) -> dict:
    """Synchronous Celery task that runs the async approval logic."""
    import asyncio
    from sqlalchemy.pool import NullPool
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

    from agentp_shared.config import db_settings
    from agentp_shared.models import Base
    from agentp_scheduler.approval import (
        approve_request,
        reject_request,
        ApprovalError,
    )

    async def _run() -> dict:
        test_url = db_settings.url
        engine = create_async_engine(test_url, poolclass=NullPool, echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            try:
                if action == "approve":
                    return await approve_request(
                        session, approval_id=approval_id, reviewer_id=reviewer_id
                    )
                elif action == "reject":
                    return await reject_request(
                        session,
                        approval_id=approval_id,
                        reviewer_id=reviewer_id,
                        reason=reason,
                    )
                else:
                    return {"ok": False, "error": f"Unknown action: {action}"}
            except ApprovalError as exc:
                return {"ok": False, "code": exc.code, "message": exc.message}
            finally:
                await session.commit()
                await engine.dispose()

    try:
        return asyncio.run(_run())
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
