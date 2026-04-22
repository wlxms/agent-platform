"""Tests for Market DB-backed service (T2.1)."""
import pytest


async def _seed_org(db):
    """Insert a minimal org row so Template FK is satisfied."""
    from agentp_shared.models import Organization
    from sqlalchemy import select
    existing = (await db.execute(select(Organization).where(Organization.id == "org-1"))).scalar_one_or_none()
    if not existing:
        db.add(Organization(id="org-1", name="Test Org"))
        await db.flush()


async def test_create_template(db_session):
    from agentp_market.service import create_template
    await _seed_org(db_session)
    result = await create_template(db_session, org_id="org-1", author_id="u1", name="Test Tpl")
    assert result["name"] == "Test Tpl"
    assert result["visibility"] == "private"
    assert result["usage_count"] == 0


async def test_list_templates_with_filter(db_session):
    from agentp_market.service import create_template, list_templates
    await _seed_org(db_session)
    await create_template(db_session, org_id="org-1", author_id="u1", name="Alpha", category="coding")
    await create_template(db_session, org_id="org-1", author_id="u1", name="Beta", category="research")
    result = await list_templates(db_session, category="coding")
    assert result["total"] == 1
    assert result["items"][0]["name"] == "Alpha"


async def test_get_template(db_session):
    from agentp_market.service import create_template, get_template
    await _seed_org(db_session)
    created = await create_template(db_session, org_id="org-1", author_id="u1", name="Get Me")
    result = await get_template(db_session, template_id=created["id"])
    assert result is not None
    assert result["name"] == "Get Me"


async def test_create_skill(db_session):
    from agentp_market.service import create_skill
    result = await create_skill(db_session, name="test-skill", description="A skill")
    assert result["name"] == "test-skill"


async def test_list_skills(db_session):
    from agentp_market.service import create_skill, list_skills
    await create_skill(db_session, name="skill-a")
    await create_skill(db_session, name="skill-b")
    result = await list_skills(db_session)
    assert result["total"] == 2


async def test_create_mcp_server(db_session):
    from agentp_market.service import create_mcp_server
    result = await create_mcp_server(db_session, name="test-mcp", transport="http")
    assert result["name"] == "test-mcp"
    assert result["transport"] == "http"


async def test_list_categories(db_session):
    from agentp_market.service import create_category, list_categories
    await create_category(db_session, name="coding", display_order=1)
    await create_category(db_session, name="research", display_order=2)
    result = await list_categories(db_session)
    assert len(result) == 2
    assert result[0]["name"] == "coding"
