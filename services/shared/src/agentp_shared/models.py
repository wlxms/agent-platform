"""SQLAlchemy database models for agent-platform."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import sqlalchemy as sa
from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

__all__ = [
    "Organization",
    "User",
    "ApiKey",
    "AgentInstance",
    "UsageRecord",
    "MemoryAsset",
    "BillingRule",
    "TaskRecord",
    "AgentConfig",
    "AgentConfigVersion",
    "Approval",
    "Budget",
    "AuditLog",
    "Template",
    "Skill",
    "McpServer",
    "Category",
]

_utcnow = lambda: datetime.now(timezone.utc)


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    parent_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
    )
    level: Mapped[int] = mapped_column(default=1)
    plan: Mapped[str] = mapped_column(String(20), default="free")
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    children: Mapped[list[Organization]] = relationship(back_populates="parent")
    parent: Mapped[Optional[Organization]] = relationship(
        back_populates="children", remote_side=[id]
    )
    users: Mapped[list[User]] = relationship(back_populates="organization")

    __table_args__ = (
        Index("ix_organizations_parent_id", "parent_id"),
        Index("ix_organizations_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<Organization id={self.id!r} name={self.name!r}>"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    org_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    hashed_password: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="member")
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    organization: Mapped[Organization] = relationship(back_populates="users")

    __table_args__ = (
        Index("ix_users_org_id", "org_id"),
        Index("ix_users_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id!r} username={self.username!r}>"


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    org_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    key_prefix: Mapped[Optional[str]] = mapped_column(String(10))
    permissions: Mapped[list[Any]] = mapped_column(
        sa.JSON, default=list, server_default="[]"
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=_utcnow
    )

    __table_args__ = (
        Index("ix_api_keys_org_id", "org_id"),
        Index("ix_api_keys_user_id", "user_id"),
        Index("ix_api_keys_key_prefix", "key_prefix"),
        Index("ix_api_keys_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<ApiKey id={self.id!r} name={self.name!r}>"


class AgentInstance(Base):
    __tablename__ = "agent_instances"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    org_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    agent_type: Mapped[str] = mapped_column(String(50), default="openharness")
    status: Mapped[str] = mapped_column(String(20), default="created")
    model: Mapped[str] = mapped_column(String(100), default="")
    config: Mapped[dict[str, Any]] = mapped_column(
        sa.JSON, default=dict, server_default="{}"
    )
    host_node: Mapped[str] = mapped_column(String(100), default="local")
    workspace_root: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=_utcnow
    )
    last_active_at: Mapped[Optional[datetime]] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    destroyed_at: Mapped[Optional[datetime]] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("ix_agent_instances_org_id", "org_id"),
        Index("ix_agent_instances_user_id", "user_id"),
        Index("ix_agent_instances_status", "status"),
        Index("ix_agent_instances_host_node", "host_node"),
    )

    def __repr__(self) -> str:
        return f"<AgentInstance id={self.id!r} name={self.name!r}>"


class UsageRecord(Base):
    __tablename__ = "usage_records"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    instance_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("agent_instances.id", ondelete="SET NULL"),
        nullable=False,
    )
    org_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
    )
    model: Mapped[str] = mapped_column(String(100), default="")
    input_tokens: Mapped[int] = mapped_column(default=0)
    output_tokens: Mapped[int] = mapped_column(default=0)
    total_tokens: Mapped[int] = mapped_column(default=0)
    cost: Mapped[float] = mapped_column(sa.Numeric(12, 6), default=0)
    timestamp: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=_utcnow
    )

    __table_args__ = (
        Index("ix_usage_records_instance_id", "instance_id"),
        Index("ix_usage_records_org_id", "org_id"),
        Index("ix_usage_records_timestamp", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<UsageRecord id={self.id!r} instance_id={self.instance_id!r}>"


class MemoryAsset(Base):
    __tablename__ = "memory_assets"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    org_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    path: Mapped[str] = mapped_column(String(1000), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), default="application/octet-stream")
    size_bytes: Mapped[int] = mapped_column(sa.BigInteger, default=0)
    storage_ref: Mapped[str] = mapped_column(String(500), default="")
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        sa.JSON, default=dict, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    __table_args__ = (
        UniqueConstraint("org_id", "path", name="uq_memory_assets_org_id_path"),
        Index("ix_memory_assets_org_id", "org_id"),
    )

    def __repr__(self) -> str:
        return f"<MemoryAsset id={self.id!r} path={self.path!r}>"


class BillingRule(Base):
    __tablename__ = "billing_rules"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    org_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
    )
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    price_per_input_token: Mapped[float] = mapped_column(
        sa.Numeric(12, 8), default=0
    )
    price_per_output_token: Mapped[float] = mapped_column(
        sa.Numeric(12, 8), default=0
    )
    effective_from: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=_utcnow
    )
    effective_until: Mapped[Optional[datetime]] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=_utcnow
    )

    __table_args__ = (
        UniqueConstraint("org_id", "model", name="uq_billing_rules_org_id_model"),
    )

    def __repr__(self) -> str:
        return f"<BillingRule id={self.id!r} model={self.model!r}>"


class TaskRecord(Base):
    __tablename__ = "task_records"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    payload: Mapped[dict[str, Any]] = mapped_column(
        sa.JSON, default=dict, server_default="{}"
    )
    result: Mapped[Optional[dict[str, Any]]] = mapped_column(sa.JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    priority: Mapped[int] = mapped_column(default=0)
    max_retries: Mapped[int] = mapped_column(default=3)
    retry_count: Mapped[int] = mapped_column(default=0)
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), default=_utcnow
    )

    __table_args__ = (
        Index("ix_task_records_type", "type"),
        Index("ix_task_records_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<TaskRecord id={self.id!r} type={self.type!r}>"


class AgentConfig(Base):
    __tablename__ = "agent_configs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    author_id: Mapped[str] = mapped_column(String, nullable=False)
    org_id: Mapped[str] = mapped_column(
        String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    visibility: Mapped[str] = mapped_column(String(20), default="private")
    status: Mapped[str] = mapped_column(String(20), default="draft")

    # 11 JSONB dimension fields per api-protocol 4.3.1
    model: Mapped[dict] = mapped_column(sa.JSON, default=dict, server_default="{}")
    litellm_params: Mapped[dict] = mapped_column(sa.JSON, default=dict, server_default="{}")
    prompt_template: Mapped[dict] = mapped_column(sa.JSON, default=dict, server_default="{}")
    tools: Mapped[list] = mapped_column(sa.JSON, default=list, server_default="[]")
    skills: Mapped[list] = mapped_column(sa.JSON, default=list, server_default="[]")
    mcp_servers: Mapped[list] = mapped_column(sa.JSON, default=list, server_default="[]")
    knowledge: Mapped[dict] = mapped_column(sa.JSON, default=dict, server_default="{}")
    memory: Mapped[dict] = mapped_column(sa.JSON, default=dict, server_default="{}")
    appearance: Mapped[dict] = mapped_column(sa.JSON, default=dict, server_default="{}")
    safety: Mapped[dict] = mapped_column(sa.JSON, default=dict, server_default="{}")
    runtime: Mapped[dict] = mapped_column(sa.JSON, default=dict, server_default="{}")

    tags: Mapped[list] = mapped_column(sa.JSON, default=list, server_default="[]")
    metadata_: Mapped[dict] = mapped_column(sa.JSON, default=dict, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        Index("ix_agent_configs_org_id", "org_id"),
        Index("ix_agent_configs_author_id", "author_id"),
        Index("ix_agent_configs_visibility", "visibility"),
    )

    def __repr__(self) -> str:
        return f"<AgentConfig id={self.id!r} name={self.name!r}>"


class AgentConfigVersion(Base):
    __tablename__ = "agent_config_versions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_config_id: Mapped[str] = mapped_column(
        String, ForeignKey("agent_configs.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    config_snapshot: Mapped[dict] = mapped_column(sa.JSON, nullable=False)
    changelog: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        Index("ix_agent_config_versions_agent_config_id", "agent_config_id"),
    )

    def __repr__(self) -> str:
        return f"<AgentConfigVersion id={self.id!r} version={self.version!r}>"


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id: Mapped[str] = mapped_column(
        String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    applicant_id: Mapped[str] = mapped_column(String, nullable=False)
    reviewer_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    template_name: Mapped[str] = mapped_column(String(100), default="")
    template_version: Mapped[str] = mapped_column(String(20), default="")
    config_snapshot: Mapped[dict] = mapped_column(sa.JSON, default=dict, server_default="{}")
    review_comment: Mapped[str] = mapped_column(String(1000), default="")
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        Index("ix_approvals_org_id", "org_id"),
        Index("ix_approvals_status", "status"),
        Index("ix_approvals_applicant_id", "applicant_id"),
    )

    def __repr__(self) -> str:
        return f"<Approval id={self.id!r} status={self.status!r}>"


class Budget(Base):
    __tablename__ = "budgets"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id: Mapped[str] = mapped_column(
        String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    threshold: Mapped[float] = mapped_column(sa.Numeric(12, 2), default=0)
    alert_rules: Mapped[dict] = mapped_column(sa.JSON, default=dict, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        UniqueConstraint("org_id", name="uq_budgets_org_id"),
    )

    def __repr__(self) -> str:
        return f"<Budget id={self.id!r} org_id={self.org_id!r}>"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    org_id: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), default="")
    resource_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    path: Mapped[str] = mapped_column(String(500), default="")
    request_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status_code: Mapped[Optional[int]] = mapped_column(sa.Integer, nullable=True)
    request_body: Mapped[dict] = mapped_column(sa.JSON, default=dict, server_default="{}")
    response_body: Mapped[dict] = mapped_column(sa.JSON, default=dict, server_default="{}")
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        Index("ix_audit_logs_org_id", "org_id"),
        Index("ix_audit_logs_timestamp", "timestamp"),
        Index("ix_audit_logs_path", "path"),
        Index("ix_audit_logs_request_id", "request_id"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id!r} action={self.action!r}>"


class Template(Base):
    __tablename__ = "templates"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id: Mapped[str] = mapped_column(
        String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), default="")
    category: Mapped[str] = mapped_column(String(50), default="general")
    visibility: Mapped[str] = mapped_column(String(20), default="private")
    author_id: Mapped[str] = mapped_column(String, nullable=False)
    config_snapshot: Mapped[dict] = mapped_column(sa.JSON, nullable=False)
    tags: Mapped[list] = mapped_column(sa.JSON, default=list, server_default="[]")
    version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    usage_count: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    __table_args__ = (
        Index("ix_templates_org_id", "org_id"),
        Index("ix_templates_category", "category"),
        Index("ix_templates_visibility", "visibility"),
    )

    def __repr__(self) -> str:
        return f"<Template id={self.id!r} name={self.name!r}>"


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(500), default="")
    author: Mapped[str] = mapped_column(String(100), default="")
    version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    package_url: Mapped[str] = mapped_column(String(500), default="")
    category: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=_utcnow)

    def __repr__(self) -> str:
        return f"<Skill id={self.id!r} name={self.name!r}>"


class McpServer(Base):
    __tablename__ = "mcp_servers"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    transport: Mapped[str] = mapped_column(String(50), default="stdio")
    description: Mapped[str] = mapped_column(String(500), default="")
    config_template: Mapped[dict] = mapped_column(sa.JSON, default=dict, server_default="{}")
    category: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        Index("ix_mcp_servers_transport", "transport"),
        Index("ix_mcp_servers_category", "category"),
    )

    def __repr__(self) -> str:
        return f"<McpServer id={self.id!r} name={self.name!r}>"


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    icon: Mapped[str] = mapped_column(String(50), default="")
    display_order: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=_utcnow)

    def __repr__(self) -> str:
        return f"<Category id={self.id!r} name={self.name!r}>"
