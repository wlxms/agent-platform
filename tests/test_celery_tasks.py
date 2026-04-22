"""T5.4 — Celery integration tests."""
from __future__ import annotations


def test_celery_app_configured():
    from agentp_scheduler.celery_app import celery

    assert celery is not None
    assert celery.main == "agentp_scheduler"


def test_celery_task_registered():
    from agentp_scheduler.celery_app import process_approval_task

    assert callable(process_approval_task)
