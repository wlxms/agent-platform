"""Unit tests for agentp_shared database models."""
import pytest
from datetime import datetime, timezone
from decimal import Decimal


class TestOrganization:
    def test_table_name(self):
        from agentp_shared.models import Organization
        assert Organization.__tablename__ == "organizations"

    def test_columns_exist(self):
        from agentp_shared.models import Organization
        mapper = Organization.__mapper__
        col_names = {c.name for c in mapper.columns}
        assert "id" in col_names
        assert "name" in col_names
        assert "parent_id" in col_names
        assert "level" in col_names
        assert "plan" in col_names
        assert "status" in col_names
        assert "created_at" in col_names
        assert "updated_at" in col_names

    def test_primary_key(self):
        from agentp_shared.models import Organization
        pk = Organization.__mapper__.primary_key
        assert len(pk) == 1
        assert pk[0].name == "id"

    def test_parent_fk(self):
        from agentp_shared.models import Organization
        mapper = Organization.__mapper__
        parent_col = mapper.columns["parent_id"]
        assert parent_col.foreign_keys

    def test_column_defaults(self):
        from agentp_shared.models import Organization
        mapper = Organization.__mapper__
        assert mapper.columns["status"].default.arg == "active"
        assert mapper.columns["plan"].default.arg == "free"
        assert mapper.columns["level"].default.arg == 1

    def test_instantiation(self):
        from agentp_shared.models import Organization
        org = Organization(id="org-1", name="Test Corp")
        assert org.name == "Test Corp"

    def test_repr(self):
        from agentp_shared.models import Organization
        org = Organization(id="org-1", name="Test Corp")
        r = repr(org)
        assert "org-1" in r
        assert "Test Corp" in r


class TestUser:
    def test_table_name(self):
        from agentp_shared.models import User
        assert User.__tablename__ == "users"

    def test_columns_exist(self):
        from agentp_shared.models import User
        col_names = {c.name for c in User.__mapper__.columns}
        assert "id" in col_names
        assert "org_id" in col_names
        assert "username" in col_names
        assert "email" in col_names
        assert "hashed_password" in col_names
        assert "role" in col_names
        assert "status" in col_names
        assert "created_at" in col_names
        assert "updated_at" in col_names

    def test_org_fk(self):
        from agentp_shared.models import User
        org_col = User.__mapper__.columns["org_id"]
        assert org_col.foreign_keys

    def test_unique_columns(self):
        from agentp_shared.models import User
        mapper = User.__mapper__
        assert mapper.columns["username"].unique is True
        assert mapper.columns["email"].unique is True

    def test_column_defaults(self):
        from agentp_shared.models import User
        mapper = User.__mapper__
        assert mapper.columns["role"].default.arg == "member"
        assert mapper.columns["status"].default.arg == "active"

    def test_instantiation(self):
        from agentp_shared.models import User
        user = User(id="u-1", org_id="org-1", username="alice", email="a@b.com")
        assert user.username == "alice"

    def test_repr(self):
        from agentp_shared.models import User
        user = User(id="u-1", org_id="org-1", username="alice", email="a@b.com")
        assert "u-1" in repr(user)
        assert "alice" in repr(user)


class TestApiKey:
    def test_table_name(self):
        from agentp_shared.models import ApiKey
        assert ApiKey.__tablename__ == "api_keys"

    def test_columns_exist(self):
        from agentp_shared.models import ApiKey
        col_names = {c.name for c in ApiKey.__mapper__.columns}
        for expected in ("id", "org_id", "user_id", "name", "key_hash",
                         "key_prefix", "permissions", "expires_at",
                         "last_used_at", "status", "created_at"):
            assert expected in col_names

    def test_key_hash_unique(self):
        from agentp_shared.models import ApiKey
        assert ApiKey.__mapper__.columns["key_hash"].unique is True

    def test_permissions_json(self):
        from agentp_shared.models import ApiKey
        import sqlalchemy as sa
        col = ApiKey.__mapper__.columns["permissions"]
        assert isinstance(col.type, sa.JSON)

    def test_column_defaults(self):
        from agentp_shared.models import ApiKey
        mapper = ApiKey.__mapper__
        assert mapper.columns["status"].default.arg == "active"
        assert mapper.columns["permissions"].default.arg([]) == []

    def test_instantiation(self):
        from agentp_shared.models import ApiKey
        key = ApiKey(id="k-1", org_id="org-1", name="my-key", key_hash="hash123")
        assert key.name == "my-key"

    def test_repr(self):
        from agentp_shared.models import ApiKey
        key = ApiKey(id="k-1", org_id="org-1", name="my-key", key_hash="hash123")
        assert "k-1" in repr(key)
        assert "my-key" in repr(key)


class TestAgentInstance:
    def test_table_name(self):
        from agentp_shared.models import AgentInstance
        assert AgentInstance.__tablename__ == "agent_instances"

    def test_columns_exist(self):
        from agentp_shared.models import AgentInstance
        col_names = {c.name for c in AgentInstance.__mapper__.columns}
        for expected in ("id", "org_id", "user_id", "name", "agent_type",
                         "status", "model", "config", "host_node",
                         "workspace_root", "created_at", "last_active_at",
                         "destroyed_at"):
            assert expected in col_names

    def test_column_defaults(self):
        from agentp_shared.models import AgentInstance
        mapper = AgentInstance.__mapper__
        assert mapper.columns["status"].default.arg == "created"
        assert mapper.columns["agent_type"].default.arg == "openharness"
        assert mapper.columns["host_node"].default.arg == "local"
        assert mapper.columns["config"].default.arg({}) == {}

    def test_instantiation(self):
        from agentp_shared.models import AgentInstance
        inst = AgentInstance(id="ai-1", org_id="org-1", user_id="u-1", name="bot")
        assert inst.name == "bot"

    def test_config_json(self):
        from agentp_shared.models import AgentInstance
        import sqlalchemy as sa
        col = AgentInstance.__mapper__.columns["config"]
        assert isinstance(col.type, sa.JSON)

    def test_instantiation(self):
        from agentp_shared.models import AgentInstance
        inst = AgentInstance(id="ai-1", org_id="org-1", user_id="u-1", name="bot")
        assert inst.name == "bot"

    def test_repr(self):
        from agentp_shared.models import AgentInstance
        inst = AgentInstance(id="ai-1", org_id="org-1", user_id="u-1", name="bot")
        assert "ai-1" in repr(inst)
        assert "bot" in repr(inst)


class TestUsageRecord:
    def test_table_name(self):
        from agentp_shared.models import UsageRecord
        assert UsageRecord.__tablename__ == "usage_records"

    def test_biginteger_pk(self):
        from agentp_shared.models import UsageRecord
        import sqlalchemy as sa
        pk = UsageRecord.__mapper__.primary_key
        assert len(pk) == 1
        assert isinstance(pk[0].type, sa.BigInteger)
        assert pk[0].autoincrement is True

    def test_columns_exist(self):
        from agentp_shared.models import UsageRecord
        col_names = {c.name for c in UsageRecord.__mapper__.columns}
        for expected in ("id", "instance_id", "org_id", "user_id", "model",
                         "input_tokens", "output_tokens", "total_tokens",
                         "cost", "timestamp"):
            assert expected in col_names

    def test_cost_numeric(self):
        from agentp_shared.models import UsageRecord
        import sqlalchemy as sa
        col = UsageRecord.__mapper__.columns["cost"]
        assert isinstance(col.type, sa.Numeric)
        assert col.type.precision == 12
        assert col.type.scale == 6

    def test_token_column_defaults(self):
        from agentp_shared.models import UsageRecord
        mapper = UsageRecord.__mapper__
        assert mapper.columns["input_tokens"].default.arg == 0
        assert mapper.columns["output_tokens"].default.arg == 0
        assert mapper.columns["total_tokens"].default.arg == 0
        assert mapper.columns["cost"].default.arg == 0

    def test_instantiation(self):
        from agentp_shared.models import UsageRecord
        rec = UsageRecord(instance_id="ai-1", org_id="org-1", user_id="u-1")
        assert rec.instance_id == "ai-1"

    def test_repr(self):
        from agentp_shared.models import UsageRecord
        rec = UsageRecord(id=42, instance_id="ai-1", org_id="org-1", user_id="u-1")
        assert "42" in repr(rec)
        assert "ai-1" in repr(rec)


class TestMemoryAsset:
    def test_table_name(self):
        from agentp_shared.models import MemoryAsset
        assert MemoryAsset.__tablename__ == "memory_assets"

    def test_columns_exist(self):
        from agentp_shared.models import MemoryAsset
        col_names = {c.name for c in MemoryAsset.__mapper__.columns}
        for expected in ("id", "org_id", "path", "content_type", "size_bytes",
                         "storage_ref", "metadata", "created_at", "updated_at"):
            assert expected in col_names

    def test_unique_constraint_org_path(self):
        from agentp_shared.db import Base
        table = Base.metadata.tables["memory_assets"]
        found = False
        for constraint in table.constraints:
            if hasattr(constraint, "columns") and len(constraint.columns) == 2:
                cols = {c.name for c in constraint.columns}
                if cols == {"org_id", "path"}:
                    found = True
                    break
        assert found, "UniqueConstraint on (org_id, path) not found"

    def test_size_bytes_is_biginteger(self):
        from agentp_shared.models import MemoryAsset
        import sqlalchemy as sa
        col = MemoryAsset.__mapper__.columns["size_bytes"]
        assert isinstance(col.type, sa.BigInteger)

    def test_column_defaults(self):
        from agentp_shared.models import MemoryAsset
        cols = {c.name: c for c in MemoryAsset.__mapper__.columns}
        assert cols["content_type"].default.arg == "application/octet-stream"
        assert cols["size_bytes"].default.arg == 0
        assert cols["storage_ref"].default.arg == ""
        assert cols["metadata"].default.arg({}) == {}

    def test_instantiation(self):
        from agentp_shared.models import MemoryAsset
        asset = MemoryAsset(id="m-1", org_id="org-1", path="/files/doc.txt")
        assert asset.path == "/files/doc.txt"

    def test_repr(self):
        from agentp_shared.models import MemoryAsset
        asset = MemoryAsset(id="m-1", org_id="org-1", path="/files/doc.txt")
        assert "m-1" in repr(asset)
        assert "/files/doc.txt" in repr(asset)


class TestBillingRule:
    def test_table_name(self):
        from agentp_shared.models import BillingRule
        assert BillingRule.__tablename__ == "billing_rules"

    def test_columns_exist(self):
        from agentp_shared.models import BillingRule
        col_names = {c.name for c in BillingRule.__mapper__.columns}
        for expected in ("id", "org_id", "model", "price_per_input_token",
                         "price_per_output_token", "effective_from",
                         "effective_until", "created_at"):
            assert expected in col_names

    def test_unique_constraint_org_model(self):
        from agentp_shared.db import Base
        table = Base.metadata.tables["billing_rules"]
        found = False
        for constraint in table.constraints:
            if hasattr(constraint, "columns") and len(constraint.columns) == 2:
                cols = {c.name for c in constraint.columns}
                if cols == {"org_id", "model"}:
                    found = True
                    break
        assert found, "UniqueConstraint on (org_id, model) not found"

    def test_price_columns_are_numeric(self):
        from agentp_shared.models import BillingRule
        import sqlalchemy as sa
        for col_name in ("price_per_input_token", "price_per_output_token"):
            col = BillingRule.__mapper__.columns[col_name]
            assert isinstance(col.type, sa.Numeric)
            assert col.type.precision == 12
            assert col.type.scale == 8

    def test_column_defaults(self):
        from agentp_shared.models import BillingRule
        mapper = BillingRule.__mapper__
        assert mapper.columns["price_per_input_token"].default.arg == 0
        assert mapper.columns["price_per_output_token"].default.arg == 0

    def test_instantiation(self):
        from agentp_shared.models import BillingRule
        rule = BillingRule(id="br-1", model="gpt-4")
        assert rule.model == "gpt-4"

    def test_repr(self):
        from agentp_shared.models import BillingRule
        rule = BillingRule(id="br-1", model="gpt-4")
        assert "br-1" in repr(rule)
        assert "gpt-4" in repr(rule)


class TestTaskRecord:
    def test_table_name(self):
        from agentp_shared.models import TaskRecord
        assert TaskRecord.__tablename__ == "task_records"

    def test_columns_exist(self):
        from agentp_shared.models import TaskRecord
        col_names = {c.name for c in TaskRecord.__mapper__.columns}
        for expected in ("id", "type", "status", "payload", "result",
                         "error_message", "priority", "max_retries",
                         "retry_count", "scheduled_at", "started_at",
                         "completed_at", "created_at"):
            assert expected in col_names

    def test_column_defaults(self):
        from agentp_shared.models import TaskRecord
        mapper = TaskRecord.__mapper__
        assert mapper.columns["status"].default.arg == "pending"
        assert mapper.columns["priority"].default.arg == 0
        assert mapper.columns["max_retries"].default.arg == 3
        assert mapper.columns["retry_count"].default.arg == 0
        assert mapper.columns["payload"].default.arg({}) == {}

    def test_instantiation(self):
        from agentp_shared.models import TaskRecord
        task = TaskRecord(id="t-1", type="deploy")
        assert task.type == "deploy"

    def test_payload_json(self):
        from agentp_shared.models import TaskRecord
        import sqlalchemy as sa
        col = TaskRecord.__mapper__.columns["payload"]
        assert isinstance(col.type, sa.JSON)

    def test_instantiation(self):
        from agentp_shared.models import TaskRecord
        task = TaskRecord(id="t-1", type="deploy")
        assert task.type == "deploy"

    def test_repr(self):
        from agentp_shared.models import TaskRecord
        task = TaskRecord(id="t-1", type="deploy")
        assert "t-1" in repr(task)
        assert "deploy" in repr(task)


class TestModelExports:
    def test_all_models_exported(self):
        from agentp_shared.models import (
            Organization, User, ApiKey, AgentInstance,
            UsageRecord, MemoryAsset, BillingRule, TaskRecord,
        )
        assert Organization is not None
        assert User is not None
        assert ApiKey is not None
        assert AgentInstance is not None
        assert UsageRecord is not None
        assert MemoryAsset is not None
        assert BillingRule is not None
        assert TaskRecord is not None

    def test_models_registered_with_base_metadata(self):
        from agentp_shared.db import Base
        from agentp_shared.models import (
            Organization, User, ApiKey, AgentInstance,
            UsageRecord, MemoryAsset, BillingRule, TaskRecord,
        )
        expected_tables = {
            "organizations", "users", "api_keys", "agent_instances",
            "usage_records", "memory_assets", "billing_rules", "task_records",
        }
        actual_tables = set(Base.metadata.tables.keys())
        assert expected_tables.issubset(actual_tables), f"Missing tables: {expected_tables - actual_tables}"

    def test_total_table_count(self):
        from agentp_shared.db import Base
        tables = set(Base.metadata.tables.keys())
        assert len(tables) >= 8, f"Expected at least 8 tables, got {len(tables)}"

    def test_unique_constraints(self):
        from agentp_shared.db import Base
        for table_name, table in Base.metadata.tables.items():
            for constraint in table.constraints:
                if hasattr(constraint, 'unique') and constraint.unique and len(constraint.columns) > 1:
                    cols = {c.name for c in constraint.columns}
                    if table_name == "memory_assets":
                        assert cols == {"org_id", "path"}, f"Unexpected unique constraint on memory_assets: {cols}"
                    if table_name == "billing_rules":
                        assert cols == {"org_id", "model"}, f"Unexpected unique constraint on billing_rules: {cols}"
