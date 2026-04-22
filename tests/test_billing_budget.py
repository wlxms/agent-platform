"""Tests for budget CRUD (T3.1)."""
import pytest


async def test_create_budget(db_session):
    from agentp_billing.service import set_budget
    result = await set_budget(db_session, org_id="org-1", threshold=500.0, alert_rules={"thresholds": [80, 90, 100]})
    assert result["threshold"] == 500.0
    assert result["alert_rules"]["thresholds"] == [80, 90, 100]


async def test_get_budget(db_session):
    from agentp_billing.service import set_budget, get_budget
    await set_budget(db_session, org_id="org-1", threshold=1000.0)
    result = await get_budget(db_session, org_id="org-1")
    assert result is not None
    assert result["threshold"] == 1000.0


async def test_get_budget_not_found(db_session):
    from agentp_billing.service import get_budget
    result = await get_budget(db_session, org_id="nonexistent")
    assert result is None


async def test_update_budget(db_session):
    from agentp_billing.service import set_budget, update_budget, get_budget
    await set_budget(db_session, org_id="org-1", threshold=500.0)
    result = await update_budget(db_session, org_id="org-1", threshold=750.0, alert_rules={"thresholds": [70, 90]})
    assert result["ok"] is True
    budget = await get_budget(db_session, org_id="org-1")
    assert budget["threshold"] == 750.0
