"""Tests for Market service — DB-backed (rewritten after T2.1 migration)."""


async def test_health():
    from httpx import AsyncClient, ASGITransport
    from agentp_market.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


async def test_list_templates(db_session):
    from agentp_market.service import create_template, list_templates
    await create_template(db_session, org_id="org-1", author_id="u1", name="T1", category="coding")
    await create_template(db_session, org_id="org-1", author_id="u1", name="T2", category="research")
    await create_template(db_session, org_id="org-1", author_id="u1", name="T3", category="general")
    result = await list_templates(db_session)
    assert result["total"] == 3
    assert result["page"] == 1
    assert len(result["items"]) == 3


async def test_list_templates_with_category_filter(db_session):
    from agentp_market.service import create_template, list_templates
    await create_template(db_session, org_id="org-1", author_id="u1", name="Alpha", category="coding")
    await create_template(db_session, org_id="org-1", author_id="u1", name="Beta", category="research")
    result = await list_templates(db_session, category="coding")
    assert result["total"] == 1
    assert result["items"][0]["category"] == "coding"


async def test_list_templates_with_keyword(db_session):
    from agentp_market.service import create_template, list_templates
    await create_template(db_session, org_id="org-1", author_id="u1", name="Research Agent", description="Deep research tool")
    await create_template(db_session, org_id="org-1", author_id="u1", name="Code Helper", description="General coding")
    result = await list_templates(db_session, keyword="research")
    assert result["total"] >= 1
    for item in result["items"]:
        assert "research" in item["name"].lower() or "research" in item.get("description", "").lower()


async def test_get_template(db_session):
    from agentp_market.service import create_template, get_template
    created = await create_template(db_session, org_id="org-1", author_id="u1", name="Get Me",
                                     description="A template", category="coding")
    result = await get_template(db_session, template_id=created["id"])
    assert result is not None
    assert result["id"] == created["id"]
    assert result["name"] == "Get Me"
    assert result["category"] == "coding"
    assert "usage_count" in result


async def test_get_template_not_found(db_session):
    from agentp_market.service import get_template
    result = await get_template(db_session, template_id="nonexistent-id")
    assert result is None


async def test_list_skills(db_session):
    from agentp_market.service import create_skill, list_skills
    await create_skill(db_session, name="Web Search", author="open", version="1.0.0")
    await create_skill(db_session, name="Code Review", author="open", version="1.0.0")
    result = await list_skills(db_session)
    assert result["total"] == 2
    for item in result["items"]:
        assert "id" in item
        assert "name" in item
        assert "description" in item


async def test_list_mcps(db_session):
    from agentp_market.service import create_mcp_server, list_mcp_servers
    await create_mcp_server(db_session, name="filesystem", transport="stdio")
    result = await list_mcp_servers(db_session)
    assert result["total"] == 1
    item = result["items"][0]
    assert "id" in item
    assert item["name"] == "filesystem"
    assert item["transport"] == "stdio"


async def test_pagination(db_session):
    from agentp_market.service import create_template, list_templates
    for i in range(5):
        await create_template(db_session, org_id="org-1", author_id="u1", name=f"Tpl {i}")
    result = await list_templates(db_session, page=1, page_size=2)
    assert result["total"] == 5
    assert len(result["items"]) == 2
    assert result["page"] == 1
    assert result["page_size"] == 2

    result2 = await list_templates(db_session, page=3, page_size=2)
    assert len(result2["items"]) == 1
    assert result2["page"] == 3
