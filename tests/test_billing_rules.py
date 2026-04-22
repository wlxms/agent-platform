"""Tests for billing rules CRUD (T3.3)."""
from __future__ import annotations

import pytest
import uuid

pytestmark = pytest.mark.asyncio(loop_scope="function")


async def test_create_billing_rule(db_session):
    from agentp_billing.service import create_billing_rule, get_billing_rule

    rule = await create_billing_rule(
        db_session,
        org_id="org-1",
        model="*",
        price_per_input_token=0.00001,
        price_per_output_token=0.00003,
    )
    assert rule["model"] == "*"
    assert rule["price_per_input_token"] == 0.00001
    fetched = await get_billing_rule(db_session, rule_id=rule["id"])
    assert fetched["price_per_output_token"] == 0.00003


async def test_list_billing_rules(db_session):
    from agentp_billing.service import create_billing_rule, list_billing_rules

    await create_billing_rule(db_session, org_id="org-1", model="openai/*", price_per_input_token=0.01)
    await create_billing_rule(db_session, org_id="org-1", model="anthropic/*", price_per_input_token=0.02)
    result = await list_billing_rules(db_session, org_id="org-1")
    assert result["total"] == 2


async def test_update_billing_rule(db_session):
    from agentp_billing.service import create_billing_rule, update_billing_rule

    rule = await create_billing_rule(db_session, org_id="org-1", model="*", price_per_input_token=0.01)
    result = await update_billing_rule(db_session, rule_id=rule["id"], price_per_input_token=0.02)
    assert result["ok"] is True


async def test_delete_billing_rule(db_session):
    from agentp_billing.service import create_billing_rule, delete_billing_rule, get_billing_rule

    rule = await create_billing_rule(db_session, org_id="org-1", model="*", price_per_input_token=0.01)
    result = await delete_billing_rule(db_session, rule_id=rule["id"])
    assert result["ok"] is True
    fetched = await get_billing_rule(db_session, rule_id=rule["id"])
    assert fetched is None
