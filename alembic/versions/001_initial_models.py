"""Initial database schema - all core tables.

Revision ID: 001
Revises:
Create Date: 2026-04-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create organizations table
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("parent_id", sa.String(), sa.ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("level", sa.Integer(), server_default="1"),
        sa.Column("plan", sa.String(20), server_default="free"),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_organizations_parent_id", "organizations", ["parent_id"])
    op.create_index("ix_organizations_status", "organizations", ["status"])

    # Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("org_id", sa.String(), sa.ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("username", sa.String(50), unique=True, nullable=False),
        sa.Column("email", sa.String(200), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(200), nullable=True),
        sa.Column("role", sa.String(20), server_default="member"),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_org_id", "users", ["org_id"])
    op.create_index("ix_users_status", "users", ["status"])

    # Create api_keys table
    op.create_table(
        "api_keys",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("org_id", sa.String(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("key_hash", sa.String(200), unique=True, nullable=False),
        sa.Column("key_prefix", sa.String(10), nullable=False),
        sa.Column("permissions", postgresql.JSON(), server_default="[]"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_api_keys_org_id", "api_keys", ["org_id"])
    op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"])
    op.create_index("ix_api_keys_key_prefix", "api_keys", ["key_prefix"])
    op.create_index("ix_api_keys_status", "api_keys", ["status"])

    # Create agent_instances table
    op.create_table(
        "agent_instances",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("org_id", sa.String(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("agent_type", sa.String(50), server_default="openharness"),
        sa.Column("status", sa.String(20), server_default="created"),
        sa.Column("model", sa.String(100), server_default=""),
        sa.Column("config", postgresql.JSON(), server_default="{}"),
        sa.Column("host_node", sa.String(100), server_default="local"),
        sa.Column("workspace_root", sa.String(500), server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("destroyed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_agent_instances_org_id", "agent_instances", ["org_id"])
    op.create_index("ix_agent_instances_user_id", "agent_instances", ["user_id"])
    op.create_index("ix_agent_instances_status", "agent_instances", ["status"])
    op.create_index("ix_agent_instances_host_node", "agent_instances", ["host_node"])

    # Create usage_records table
    op.create_table(
        "usage_records",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("instance_id", sa.String(), sa.ForeignKey("agent_instances.id", ondelete="SET NULL"), nullable=False),
        sa.Column("org_id", sa.String(), sa.ForeignKey("organizations.id", ondelete="SET NULL"), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=False),
        sa.Column("model", sa.String(100), server_default=""),
        sa.Column("input_tokens", sa.Integer(), server_default="0"),
        sa.Column("output_tokens", sa.Integer(), server_default="0"),
        sa.Column("total_tokens", sa.Integer(), server_default="0"),
        sa.Column("cost", sa.Numeric(12, 6), server_default="0"),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_usage_records_instance_id", "usage_records", ["instance_id"])
    op.create_index("ix_usage_records_org_id", "usage_records", ["org_id"])
    op.create_index("ix_usage_records_timestamp", "usage_records", ["timestamp"])

    # Create memory_assets table
    op.create_table(
        "memory_assets",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("org_id", sa.String(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("path", sa.String(1000), nullable=False),
        sa.Column("content_type", sa.String(100), server_default="application/octet-stream"),
        sa.Column("size_bytes", sa.BigInteger(), server_default="0"),
        sa.Column("storage_ref", sa.String(500), server_default=""),
        sa.Column("metadata_", postgresql.JSON(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("org_id", "path", name="uq_memory_assets_org_path"),
    )
    op.create_index("ix_memory_assets_org_id", "memory_assets", ["org_id"])

    # Create billing_rules table
    op.create_table(
        "billing_rules",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("org_id", sa.String(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("price_per_input_token", sa.Numeric(12, 8), server_default="0"),
        sa.Column("price_per_output_token", sa.Numeric(12, 8), server_default="0"),
        sa.Column("effective_from", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("effective_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("org_id", "model", name="uq_billing_rules_org_model"),
    )

    # Create task_records table
    op.create_table(
        "task_records",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("payload", postgresql.JSON(), server_default="{}"),
        sa.Column("result", postgresql.JSON(), nullable=True),
        sa.Column("error_message", sa.String(500), nullable=True),
        sa.Column("priority", sa.Integer(), server_default="0"),
        sa.Column("max_retries", sa.Integer(), server_default="3"),
        sa.Column("retry_count", sa.Integer(), server_default="0"),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_task_records_type", "task_records", ["type"])
    op.create_index("ix_task_records_status", "task_records", ["status"])


def downgrade() -> None:
    op.drop_table("task_records")
    op.drop_table("billing_rules")
    op.drop_table("memory_assets")
    op.drop_table("usage_records")
    op.drop_table("agent_instances")
    op.drop_table("api_keys")
    op.drop_table("users")
    op.drop_table("organizations")
