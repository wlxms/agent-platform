"""Host service: manages agent instances via SDK and syncs to PostgreSQL."""
from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from agent_orchestrator import OrchestratorClient
from agentp_shared.api_mapping import AgentMappingSettings, CreateAgentRequest, InstanceMapper
from agentp_shared.models import AgentInstance


class HostError(Exception):
    """Business-level error for host operations."""
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class HostService:
    def __init__(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="agentp-host-")
        self.mapper = InstanceMapper(
            settings=AgentMappingSettings(
                workspace_base=f"{self.temp_dir}/workspaces",
                templates_base=f"{self.temp_dir}/templates",
                allowed_roots=[self.temp_dir],
            )
        )
        self.client = OrchestratorClient(
            allowed_roots=[self.temp_dir],
            runtime="noop",
            db_path=str(Path(self.temp_dir) / "instances.db"),
        )

    # ---- SDK-backed operations (sync) ----

    def create_instance(self, req: CreateAgentRequest) -> dict:
        sdk_req = self.mapper.to_sdk_request(req)
        record = self.client.create_instance(sdk_req)
        return _record_to_dict(record)

    def list_instances(self) -> list[dict]:
        instances = self.client.list_instances()
        return [_record_to_dict(r) for r in instances]

    def get_instance(self, instance_id: str) -> dict | None:
        try:
            record = self.client.get_instance(instance_id)
            return _record_to_dict(record)
        except Exception:
            return None

    def destroy_instance(self, instance_id: str) -> bool:
        try:
            result = self.client.destroy_instance(instance_id)
            return result.deleted
        except Exception:
            return False

    def send_message(self, instance_id: str, prompt: str, model: str | None = None) -> dict:
        try:
            result = self.client.send_message(
                instance_id=instance_id,
                prompt=prompt,
                model=model,
                max_turns=1,
            )
            return {
                "instance_id": result.instance_id,
                "reply_text": result.reply_text,
                "model": result.model,
            }
        except Exception as e:
            raise HostError(code="UPSTREAM_UNAVAILABLE", message=f"Message failed: {e}", status_code=502) from e


# ---- DB-synced operations (async) ----

async def sync_create_to_db(
    db: AsyncSession,
    *,
    instance_id: str,
    name: str,
    org_id: str,
    user_id: str,
    model: str = "",
    status: str = "created",
    host_node: str = "local",
) -> dict:
    """Write instance record to PostgreSQL (called after SDK create)."""
    now = datetime.now(timezone.utc)
    inst = AgentInstance(
        id=instance_id,
        org_id=org_id,
        user_id=user_id,
        name=name,
        agent_type="openharness",
        status=status,
        model=model,
        host_node=host_node,
    )
    db.add(inst)
    await db.flush()
    return _db_instance_to_dict(inst)


async def sync_destroy_in_db(db: AsyncSession, *, instance_id: str) -> bool:
    """Mark instance as destroyed in PostgreSQL."""
    result = await db.execute(
        select(AgentInstance).where(AgentInstance.id == instance_id)
    )
    inst = result.scalar_one_or_none()
    if inst is None:
        return False
    inst.status = "destroyed"
    inst.destroyed_at = datetime.now(timezone.utc)
    await db.flush()
    return True


async def list_instances_from_db(
    db: AsyncSession,
    *,
    org_id: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """List instances from PostgreSQL."""
    query = select(AgentInstance).where(AgentInstance.status != "destroyed")
    if org_id:
        query = query.where(AgentInstance.org_id == org_id)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    query = query.order_by(AgentInstance.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(query)).scalars().all()

    return {
        "items": [_db_instance_to_dict(r) for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def get_instance_from_db(
    db: AsyncSession, *, instance_id: str,
) -> dict | None:
    result = await db.execute(
        select(AgentInstance).where(
            AgentInstance.id == instance_id,
            AgentInstance.status != "destroyed",
        )
    )
    inst = result.scalar_one_or_none()
    return _db_instance_to_dict(inst) if inst else None


async def seed_default_org(db: AsyncSession) -> None:
    """Ensure org-root exists in DB for FK constraints."""
    from sqlalchemy import select as sa_select
    from agentp_shared.models import Organization
    for org_id, org_name in [("org-root", "Root Organization")]:
        r = await db.execute(sa_select(Organization).where(Organization.id == org_id))
        if r.scalar_one_or_none() is None:
            db.add(Organization(id=org_id, name=org_name))


def _record_to_dict(record) -> dict:
    return {
        "id": record.instance_id,
        "guid": record.instance_id,
        "name": record.name,
        "status": record.status,
        "host": record.host,
        "workspace_path": record.workspace_path,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
    }


def _db_instance_to_dict(inst: AgentInstance) -> dict:
    return {
        "id": inst.id,
        "guid": inst.id,
        "name": inst.name,
        "status": inst.status,
        "host": inst.host_node,
        "model": inst.model or "",
        "agent_type": inst.agent_type,
        "workspace_path": inst.workspace_root or "",
        "org_id": inst.org_id,
        "user_id": inst.user_id,
        "created_at": inst.created_at.isoformat() if inst.created_at else None,
        "updated_at": inst.last_active_at.isoformat() if inst.last_active_at else None,
    }
