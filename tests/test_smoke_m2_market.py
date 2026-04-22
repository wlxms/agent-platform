"""M2 Market smoke tests — verifies all market endpoints via DB-backed service.

These tests use the db_session fixture (no running service required).
Run: pytest tests/test_smoke_m2_market.py -v
"""
import pytest


async def _seed_org(db, org_id="org-s"):
    """Create a minimal organization row to satisfy FK constraints."""
    from sqlalchemy import select
    from agentp_shared.models import Organization
    existing = (await db.execute(select(Organization).where(Organization.id == org_id))).scalar_one_or_none()
    if not existing:
        db.add(Organization(id=org_id, name=f"Smoke Org {org_id}"))
        await db.flush()


class TestTemplateEndpoints:
    """Smoke: template CRUD and list/filter."""

    async def test_create_and_get_template(self, db_session):
        from agentp_market.service import create_template, get_template
        await _seed_org(db_session)
        tpl = await create_template(db_session, org_id="org-s", author_id="u-s", name="Smoke Tpl",
                                     description="smoke test", category="smoke")
        assert tpl["id"]
        assert tpl["name"] == "Smoke Tpl"
        fetched = await get_template(db_session, template_id=tpl["id"])
        assert fetched["name"] == "Smoke Tpl"

    async def test_list_templates_empty(self, db_session):
        from agentp_market.service import list_templates
        result = await list_templates(db_session)
        assert result["total"] == 0
        assert result["items"] == []

    async def test_list_templates_with_filter(self, db_session):
        from agentp_market.service import create_template, list_templates
        await _seed_org(db_session)
        await create_template(db_session, org_id="org-s", author_id="u-s", name="A", category="x")
        await create_template(db_session, org_id="org-s", author_id="u-s", name="B", category="y")
        r = await list_templates(db_session, category="x")
        assert r["total"] == 1

    async def test_get_template_not_found(self, db_session):
        from agentp_market.service import get_template
        assert await get_template(db_session, template_id="nope") is None


class TestSkillEndpoints:
    """Smoke: skill CRUD and list."""

    async def test_create_and_list_skills(self, db_session):
        from agentp_market.service import create_skill, list_skills
        await create_skill(db_session, name="s1", version="1.0")
        await create_skill(db_session, name="s2", version="2.0")
        result = await list_skills(db_session)
        assert result["total"] == 2

    async def test_list_skills_keyword(self, db_session):
        from agentp_market.service import create_skill, list_skills
        await create_skill(db_session, name="web-search-tool", description="Search the web")
        result = await list_skills(db_session, keyword="web")
        assert result["total"] == 1


class TestMcpEndpoints:
    """Smoke: MCP server CRUD and list."""

    async def test_create_and_list_mcps(self, db_session):
        from agentp_market.service import create_mcp_server, list_mcp_servers
        await create_mcp_server(db_session, name="fs", transport="stdio")
        await create_mcp_server(db_session, name="http-srv", transport="http")
        result = await list_mcp_servers(db_session)
        assert result["total"] == 2


class TestCategoryEndpoints:
    """Smoke: category list."""

    async def test_create_and_list_categories(self, db_session):
        from agentp_market.service import create_category, list_categories
        await create_category(db_session, name="cat1", display_order=2)
        await create_category(db_session, name="cat0", display_order=1)
        result = await list_categories(db_session)
        assert len(result) == 2
        assert result[0]["name"] == "cat0"  # ordered by display_order


class TestBuilderConfigCRUD:
    """Smoke: AgentConfig builder endpoints."""

    async def test_create_get_update_delete_config(self, db_session):
        from agentp_market.service import create_config, get_config, update_config, delete_config
        await _seed_org(db_session)
        created = await create_config(db_session, org_id="org-s", author_id="u-s", name="Builder Smoke")
        assert created["version"] == "1.0.0"
        fetched = await get_config(db_session, config_id=created["id"])
        assert fetched["name"] == "Builder Smoke"

        updated = await update_config(db_session, config_id=created["id"], name="Updated")
        assert updated["version"] == "1.0.1"

        await delete_config(db_session, config_id=created["id"])
        assert await get_config(db_session, config_id=created["id"]) is None

    async def test_list_configs(self, db_session):
        from agentp_market.service import create_config, list_configs
        await _seed_org(db_session)
        await create_config(db_session, org_id="org-s", author_id="u-s", name="C1")
        await create_config(db_session, org_id="org-s", author_id="u-s", name="C2")
        result = await list_configs(db_session, org_id="org-s")
        assert result["total"] == 2

    async def test_duplicate_config(self, db_session):
        from agentp_market.service import create_config, duplicate_config
        await _seed_org(db_session)
        created = await create_config(db_session, org_id="org-s", author_id="u-s", name="Original")
        dup = await duplicate_config(db_session, config_id=created["id"], name="Clone")
        assert dup["id"] != created["id"]
        assert dup["name"] == "Clone"

    async def test_publish_config(self, db_session):
        from agentp_market.service import create_config, publish_config, get_template
        await _seed_org(db_session)
        created = await create_config(db_session, org_id="org-s", author_id="u-s", name="Publish")
        result = await publish_config(db_session, config_id=created["id"], visibility="org", category="smoke")
        assert result["ok"] is True
        assert result["template_id"] is not None
        tpl = await get_template(db_session, template_id=result["template_id"])
        assert tpl is not None

    async def test_config_versions(self, db_session):
        from agentp_market.service import create_config, update_config, get_config_versions
        await _seed_org(db_session)
        created = await create_config(db_session, org_id="org-s", author_id="u-s", name="V")
        await update_config(db_session, config_id=created["id"], name="V2")
        versions = await get_config_versions(db_session, config_id=created["id"])
        assert versions["total"] >= 2


class TestValidationEndpoint:
    """Smoke: config validation."""

    def test_validate_valid_config(self):
        from agentp_market.service import validate_config
        r = validate_config(personality={"system_prompt": "Hi"})
        assert r["valid"] is True

    def test_validate_invalid_config(self):
        from agentp_market.service import validate_config
        r = validate_config(personality={"system_prompt": ""})
        assert r["valid"] is False
        assert len(r["errors"]) > 0

    def test_validate_full(self):
        from agentp_market.service import validate_config_full
        r = validate_config_full({"personality": {"system_prompt": "Help"}, "permissions": {"mode": "default"}})
        assert r["valid"] is True


class TestImportExport:
    """Smoke: config import/export."""

    def test_export_json(self):
        from agentp_market.service import export_config
        import json
        data = {"name": "X", "model": {"provider": "litellm"}}
        result = export_config(data, format="json")
        parsed = json.loads(result)
        assert parsed["name"] == "X"
        assert "id" not in parsed

    def test_export_yaml(self):
        from agentp_market.service import export_config
        import yaml
        data = {"name": "Y", "model": {"provider": "litellm"}}
        result = export_config(data, format="yaml")
        parsed = yaml.safe_load(result)
        assert parsed["name"] == "Y"

    def test_import_json(self):
        from agentp_market.service import import_config
        result = import_config('{"name": "Imp"}', source="json")
        assert result["name"] == "Imp"

    def test_import_yaml(self):
        from agentp_market.service import import_config
        result = import_config("name: ImpY\n", source="yaml")
        assert result["name"] == "ImpY"

    def test_import_invalid_raises(self):
        from agentp_market.service import import_config, MarketError
        with pytest.raises(MarketError):
            import_config("{bad", source="json")
