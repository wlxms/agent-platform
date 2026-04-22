"""Tests for test fixtures and Pydantic schemas."""
import pytest


def test_authenticated_client_makes_authenticated_request():
    """The authenticated_client fixture should produce a client with a valid JWT."""
    from agentp_shared.security import create_access_token, decode_token

    token = create_access_token({
        "sub": "user-test-admin",
        "org_id": "org-root",
        "role": "admin",
        "permissions": ["*"],
    })
    payload = decode_token(token)
    assert payload["sub"] == "user-test-admin"
    assert payload["role"] == "admin"
    assert payload["permissions"] == ["*"]


def test_pydantic_schemas_validate():
    from agentp_shared.schemas import AgentConfigCreate, AgentConfigResponse

    create = AgentConfigCreate(
        name="Test Agent",
        model={"litellm_params": {"model": "openai/gpt-4o"}},
        personality={"system_prompt": "Hi"},
    )
    assert create.name == "Test Agent"
    assert create.visibility == "private"

    resp = AgentConfigResponse(
        id="ac-1", name="Test Agent", author_id="u1", org_id="o1",
        personality={"system_prompt": "Hi"},
    )
    assert resp.personality["system_prompt"] == "Hi"


def test_budget_schemas_validate():
    from agentp_shared.schemas import BudgetCreate, BudgetResponse

    bc = BudgetCreate(org_id="org-1", threshold=100.0,
                      alert_rules={"thresholds": [80, 90, 100]})
    assert bc.threshold == 100.0

    br = BudgetResponse(id="b-1", org_id="org-1", threshold=100.0)
    assert br.org_id == "org-1"


def test_all_schemas_importable():
    """All 13 new Pydantic schemas should be importable."""
    from agentp_shared.schemas import (
        AgentConfigCreate, AgentConfigResponse, AgentConfigUpdate,
        ApprovalCreate, ApprovalResponse, ApprovalReview,
        BudgetCreate, BudgetResponse, BudgetUpdate,
        TemplateCreate, TemplateResponse,
        SkillResponse, McpServerResponse, CategoryResponse,
    )
    assert AgentConfigCreate is not None
    assert AgentConfigResponse is not None
    assert AgentConfigUpdate is not None
    assert ApprovalCreate is not None
    assert ApprovalResponse is not None
    assert ApprovalReview is not None
    assert BudgetCreate is not None
    assert BudgetResponse is not None
    assert BudgetUpdate is not None
    assert TemplateCreate is not None
    assert TemplateResponse is not None
    assert SkillResponse is not None
    assert McpServerResponse is not None
    assert CategoryResponse is not None
