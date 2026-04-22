"""Tests for multi-level org aggregation (T3.4)."""
import pytest


async def test_org_summary_aggregates_child_orgs(db_session):
    from agentp_billing.service import get_org_summary
    result = await get_org_summary(db_session, org_id="org-1", period="month")
    assert "total_tokens" in result
    assert "total_cost" in result
    assert "by_org" in result


async def test_by_org_includes_child_breakdown(db_session):
    from agentp_billing.service import get_org_summary
    result = await get_org_summary(db_session, org_id="org-1", period="month")
    assert isinstance(result["by_org"], list)


async def test_org_summary_includes_budget(db_session):
    from agentp_billing.service import get_org_summary, set_budget
    await set_budget(db_session, org_id="org-1", threshold=1000.0)
    result = await get_org_summary(db_session, org_id="org-1", period="month")
    assert result["budget"] == 1000.0
    assert "budget_remaining" in result
