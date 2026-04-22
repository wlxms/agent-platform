"""Tests for Builder config CRUD (T2.2)."""


async def _seed_org(db):
    """Insert a minimal org row so AgentConfig FK is satisfied."""
    from agentp_shared.models import Organization
    from sqlalchemy import select
    existing = (await db.execute(select(Organization).where(Organization.id == "org-1"))).scalar_one_or_none()
    if not existing:
        db.add(Organization(id="org-1", name="Test Org"))
        await db.flush()


async def test_create_config(db_session):
    from agentp_market.service import create_config, get_config
    await _seed_org(db_session)
    result = await create_config(db_session, org_id="org-1", author_id="u1", name="My Config")
    assert result["name"] == "My Config"
    assert result["version"] == "1.0.0"
    fetched = await get_config(db_session, config_id=result["id"])
    assert fetched is not None


async def test_update_config(db_session):
    from agentp_market.service import create_config, update_config
    await _seed_org(db_session)
    created = await create_config(db_session, org_id="org-1", author_id="u1", name="V1 Config")
    result = await update_config(db_session, config_id=created["id"], name="V2 Config")
    assert result["ok"] is True
    assert result["version"] == "1.0.1"


async def test_delete_config(db_session):
    from agentp_market.service import create_config, delete_config, get_config
    await _seed_org(db_session)
    created = await create_config(db_session, org_id="org-1", author_id="u1", name="Del Me")
    await delete_config(db_session, config_id=created["id"])
    assert await get_config(db_session, config_id=created["id"]) is None


async def test_publish_config_creates_template(db_session):
    from agentp_market.service import create_config, publish_config
    await _seed_org(db_session)
    created = await create_config(db_session, org_id="org-1", author_id="u1", name="Publish Me")
    result = await publish_config(db_session, config_id=created["id"], visibility="org", category="coding", tags=["test"])
    assert result["ok"] is True
    assert result["template_id"] is not None


async def test_duplicate_config(db_session):
    from agentp_market.service import create_config, duplicate_config
    await _seed_org(db_session)
    created = await create_config(db_session, org_id="org-1", author_id="u1", name="Original")
    dup = await duplicate_config(db_session, config_id=created["id"], name="Copy")
    assert dup["id"] != created["id"]
    assert dup["name"] == "Copy"


async def test_validate_config():
    from agentp_market.service import validate_config
    result = validate_config(personality={"system_prompt": "Hi"}, model={"provider": "litellm"})
    assert result["valid"] is True
    assert len(result["warnings"]) >= 0


async def test_validate_config_errors():
    from agentp_market.service import validate_config
    result = validate_config(personality={"system_prompt": ""})
    assert result["valid"] is False
    assert any("system_prompt" in str(e) for e in result["errors"])


async def test_get_config_versions(db_session):
    from agentp_market.service import create_config, update_config, get_config_versions
    await _seed_org(db_session)
    created = await create_config(db_session, org_id="org-1", author_id="u1", name="Versioned")
    await update_config(db_session, config_id=created["id"], name="V1.1")
    versions = await get_config_versions(db_session, config_id=created["id"])
    assert versions["total"] >= 2
