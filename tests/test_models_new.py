"""Unit tests for the 9 new SQLAlchemy models."""
import pytest
from datetime import datetime, timezone


class TestAgentConfig:
    def test_table_name(self):
        from agentp_shared.models import AgentConfig
        assert AgentConfig.__tablename__ == "agent_configs"

    def test_columns_exist(self):
        from agentp_shared.models import AgentConfig
        col_names = {c.name for c in AgentConfig.__mapper__.columns}
        for expected in (
            "id", "name", "author_id", "org_id", "version",
            "visibility", "status", "model", "litellm_params",
            "prompt_template", "tools", "skills", "mcp_servers",
            "knowledge", "memory", "appearance", "safety", "runtime",
            "tags", "metadata_", "created_at", "updated_at",
        ):
            assert expected in col_names, f"Missing column: {expected}"

    def test_column_defaults(self):
        from agentp_shared.models import AgentConfig
        mapper = AgentConfig.__mapper__
        assert mapper.columns["visibility"].default.arg == "private"
        assert mapper.columns["status"].default.arg == "draft"
        assert mapper.columns["version"].default.arg == "1.0.0"

    def test_instantiation(self):
        from agentp_shared.models import AgentConfig
        config = AgentConfig(name="Test Agent", author_id="u1", org_id="o1",
                             model={"litellm_params": {"model": "openai/gpt-4o"}})
        assert config.name == "Test Agent"
        assert config.model["litellm_params"]["model"] == "openai/gpt-4o"


class TestAgentConfigVersion:
    def test_table_name(self):
        from agentp_shared.models import AgentConfigVersion
        assert AgentConfigVersion.__tablename__ == "agent_config_versions"

    def test_fk_to_agent_config(self):
        from agentp_shared.models import AgentConfigVersion
        col = AgentConfigVersion.__mapper__.columns["agent_config_id"]
        assert col.foreign_keys

    def test_instantiation(self):
        from agentp_shared.models import AgentConfigVersion
        v = AgentConfigVersion(agent_config_id="ac-1", version="1.0.0",
                               config_snapshot={"model": "gpt-4"})
        assert v.version == "1.0.0"


class TestApproval:
    def test_table_name(self):
        from agentp_shared.models import Approval
        assert Approval.__tablename__ == "approvals"

    def test_columns_exist(self):
        from agentp_shared.models import Approval
        col_names = {c.name for c in Approval.__mapper__.columns}
        for expected in ("id", "org_id", "applicant_id", "reviewer_id",
                         "status", "template_name", "template_version",
                         "config_snapshot", "review_comment",
                         "reviewed_at", "created_at"):
            assert expected in col_names

    def test_column_defaults(self):
        from agentp_shared.models import Approval
        mapper = Approval.__mapper__
        assert mapper.columns["status"].default.arg == "pending"

    def test_instantiation(self):
        from agentp_shared.models import Approval
        a = Approval(org_id="o1", applicant_id="u1",
                     template_name="Code Reviewer")
        assert a.template_name == "Code Reviewer"


class TestBudget:
    def test_table_name(self):
        from agentp_shared.models import Budget
        assert Budget.__tablename__ == "budgets"

    def test_unique_constraint_org_id(self):
        from agentp_shared.db import Base
        table = Base.metadata.tables["budgets"]
        found = any(
            hasattr(c, "columns") and len(c.columns) == 1 and
            any(col.name == "org_id" for col in c.columns)
            for c in table.constraints
        )
        assert found, "UniqueConstraint on org_id not found"

    def test_instantiation(self):
        from agentp_shared.models import Budget
        b = Budget(org_id="org-1", threshold=1000.00,
                   alert_rules={"thresholds": [80, 90, 100]})
        assert float(b.threshold) == 1000.00
        assert b.alert_rules["thresholds"] == [80, 90, 100]


class TestAuditLog:
    def test_table_name(self):
        from agentp_shared.models import AuditLog
        assert AuditLog.__tablename__ == "audit_logs"

    def test_biginteger_pk(self):
        import sqlalchemy as sa
        from agentp_shared.models import AuditLog
        pk = AuditLog.__mapper__.primary_key
        assert isinstance(pk[0].type, sa.BigInteger)

    def test_instantiation(self):
        from agentp_shared.models import AuditLog
        log = AuditLog(org_id="o1", action="create_agent",
                       resource_type="agent", resource_id="a1",
                       path="/api/v1/agents", request_id="req-123",
                       status_code=201)
        assert log.action == "create_agent"
        assert log.status_code == 201


class TestTemplate:
    def test_table_name(self):
        from agentp_shared.models import Template
        assert Template.__tablename__ == "templates"

    def test_columns_exist(self):
        from agentp_shared.models import Template
        col_names = {c.name for c in Template.__mapper__.columns}
        for expected in ("id", "org_id", "name", "description", "category",
                         "visibility", "author_id", "config_snapshot", "tags",
                         "version", "usage_count", "created_at", "updated_at"):
            assert expected in col_names

    def test_column_defaults(self):
        from agentp_shared.models import Template
        mapper = Template.__mapper__
        assert mapper.columns["usage_count"].default.arg == 0
        assert mapper.columns["category"].default.arg == "general"

    def test_instantiation(self):
        from agentp_shared.models import Template
        t = Template(org_id="o1", name="T1", author_id="u1",
                     config_snapshot={"model": "gpt-4"})
        assert t.name == "T1"


class TestSkill:
    def test_table_name(self):
        from agentp_shared.models import Skill
        assert Skill.__tablename__ == "skills"

    def test_name_unique(self):
        from agentp_shared.models import Skill
        assert Skill.__mapper__.columns["name"].unique is True

    def test_instantiation(self):
        from agentp_shared.models import Skill
        s = Skill(name="search", description="Search files", author="admin",
                  version="1.0.0", package_url="pip://oh-skill-search",
                  category="utility")
        assert s.name == "search"
        assert s.category == "utility"


class TestMcpServer:
    def test_table_name(self):
        from agentp_shared.models import McpServer
        assert McpServer.__tablename__ == "mcp_servers"

    def test_name_unique(self):
        from agentp_shared.models import McpServer
        assert McpServer.__mapper__.columns["name"].unique is True

    def test_instantiation(self):
        from agentp_shared.models import McpServer
        m = McpServer(name="github", transport="http", description="GitHub MCP",
                      config_template={"url": ""}, category="vcs")
        assert m.transport == "http"


class TestCategory:
    def test_table_name(self):
        from agentp_shared.models import Category
        assert Category.__tablename__ == "categories"

    def test_instantiation(self):
        from agentp_shared.models import Category
        c = Category(name="code_development", icon="code", display_order=1)
        assert c.name == "code_development"
        assert c.display_order == 1
