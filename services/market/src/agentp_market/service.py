"""Market service — SQLAlchemy-backed CRUD for templates, skills, MCP servers, categories."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import yaml

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from agentp_shared.models import Template, Skill, McpServer, Category, AgentConfig, AgentConfigVersion
from agentp_shared.responses import list_response

_utcnow = lambda: datetime.now(timezone.utc)


class MarketError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code


# --- Templates ---

async def create_template(db: AsyncSession, *, org_id: str, author_id: str, name: str,
                          description: str = "", category: str = "",
                          visibility: str = "private", tags: list | None = None,
                          config_snapshot: dict | None = None) -> dict:
    tpl = Template(
        id=str(uuid.uuid4()), org_id=org_id, author_id=author_id, name=name,
        description=description, category=category, visibility=visibility,
        tags=tags or [], config_snapshot=config_snapshot or {},
        usage_count=0,
    )
    db.add(tpl)
    await db.flush()
    return _tpl_to_dict(tpl)


async def get_template(db: AsyncSession, *, template_id: str) -> dict | None:
    result = await db.execute(select(Template).where(Template.id == template_id))
    tpl = result.scalar_one_or_none()
    return _tpl_to_dict(tpl) if tpl else None


async def list_templates(db: AsyncSession, *, category: str | None = None,
                         keyword: str | None = None, page: int = 1, page_size: int = 20) -> dict:
    q = select(Template)
    if category:
        q = q.where(Template.category == category)
    if keyword:
        like = f"%{keyword}%"
        q = q.where(Template.name.ilike(like) | Template.description.ilike(like))
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    q = q.order_by(Template.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(q)).scalars().all()
    return list_response([_tpl_to_dict(r) for r in rows], total, page, page_size)


# --- Skills ---

async def create_skill(db: AsyncSession, *, name: str, description: str = "",
                       author: str = "", version: str = "", package_url: str = "",
                       category: str = "") -> dict:
    skill = Skill(
        id=str(uuid.uuid4()), name=name, description=description, author=author,
        version=version, package_url=package_url, category=category,
    )
    db.add(skill)
    await db.flush()
    return _skill_to_dict(skill)


async def get_skill(db: AsyncSession, *, skill_id: str) -> dict | None:
    result = await db.execute(select(Skill).where(Skill.id == skill_id))
    s = result.scalar_one_or_none()
    return _skill_to_dict(s) if s else None


async def list_skills(db: AsyncSession, *, keyword: str | None = None,
                      page: int = 1, page_size: int = 20) -> dict:
    q = select(Skill)
    if keyword:
        like = f"%{keyword}%"
        q = q.where(Skill.name.ilike(like) | Skill.description.ilike(like))
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    q = q.order_by(Skill.name.asc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(q)).scalars().all()
    return list_response([_skill_to_dict(r) for r in rows], total, page, page_size)


# --- MCP Servers ---

async def create_mcp_server(db: AsyncSession, *, name: str, transport: str,
                            description: str = "", config_template: dict | None = None,
                            category: str = "") -> dict:
    mcp = McpServer(
        id=str(uuid.uuid4()), name=name, transport=transport,
        description=description, config_template=config_template or {},
        category=category,
    )
    db.add(mcp)
    await db.flush()
    return _mcp_to_dict(mcp)


async def get_mcp_server(db: AsyncSession, *, mcp_id: str) -> dict | None:
    result = await db.execute(select(McpServer).where(McpServer.id == mcp_id))
    m = result.scalar_one_or_none()
    return _mcp_to_dict(m) if m else None


async def list_mcp_servers(db: AsyncSession, *, keyword: str | None = None,
                           page: int = 1, page_size: int = 20) -> dict:
    q = select(McpServer)
    if keyword:
        like = f"%{keyword}%"
        q = q.where(McpServer.name.ilike(like) | McpServer.description.ilike(like))
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    q = q.order_by(McpServer.name.asc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(q)).scalars().all()
    return list_response([_mcp_to_dict(r) for r in rows], total, page, page_size)


# --- Categories ---

async def create_category(db: AsyncSession, *, name: str, icon: str | None = None,
                          display_order: int = 0) -> dict:
    cat = Category(id=str(uuid.uuid4()), name=name, icon=icon, display_order=display_order)
    db.add(cat)
    await db.flush()
    return _cat_to_dict(cat)


async def list_categories(db: AsyncSession) -> list[dict]:
    result = await db.execute(select(Category).order_by(Category.display_order.asc()))
    return [_cat_to_dict(c) for c in result.scalars().all()]


# --- Converters ---

def _tpl_to_dict(tpl: Template) -> dict:
    return {
        "id": tpl.id, "name": tpl.name, "description": tpl.description,
        "category": tpl.category, "visibility": tpl.visibility or "private",
        "tags": tpl.tags or [], "config_snapshot": tpl.config_snapshot or {},
        "usage_count": tpl.usage_count or 0,
        "created_at": tpl.created_at.isoformat() if tpl.created_at else None,
    }


def _skill_to_dict(s: Skill) -> dict:
    return {
        "id": s.id, "name": s.name, "description": s.description,
        "author": s.author or "", "version": s.version or "",
        "package_url": s.package_url or "", "category": s.category or "",
    }


def _mcp_to_dict(m: McpServer) -> dict:
    return {
        "id": m.id, "name": m.name, "transport": m.transport,
        "description": m.description or "",
        "config_template": m.config_template or {}, "category": m.category or "",
    }


def _cat_to_dict(c: Category) -> dict:
    return {
        "id": c.id, "name": c.name, "icon": c.icon,
        "display_order": c.display_order or 0,
    }

# --- AgentConfig (Builder) ---

_ALLOWED_CONFIG_FIELDS = {
    "description", "visibility", "personality", "model", "tools", "skills",
    "mcp_servers", "workspace", "permissions", "appearance", "category",
    "prompt_template", "litellm_params", "knowledge", "memory", "safety",
    "runtime", "tags", "metadata_",
}


async def create_config(db: AsyncSession, *, org_id: str, author_id: str, name: str, **fields) -> dict:
    safe_fields = {k: v for k, v in fields.items() if k in _ALLOWED_CONFIG_FIELDS}
    config = AgentConfig(
        id=str(uuid.uuid4()), org_id=org_id, author_id=author_id, name=name, **safe_fields
    )
    db.add(config)
    await db.flush()
    await _save_version(db, config_id=config.id, version=config.version, changelog="Initial version")
    return _config_to_dict(config)


async def get_config(db: AsyncSession, *, config_id: str) -> dict | None:
    result = await db.execute(select(AgentConfig).where(AgentConfig.id == config_id))
    c = result.scalar_one_or_none()
    return _config_to_dict(c) if c else None


async def update_config(db: AsyncSession, *, config_id: str, **fields) -> dict:
    result = await db.execute(select(AgentConfig).where(AgentConfig.id == config_id))
    config = result.scalar_one_or_none()
    if config is None:
        raise MarketError(code="NOT_FOUND", message="Config not found")
    for k, v in fields.items():
        if v is not None and hasattr(config, k) and k in _ALLOWED_CONFIG_FIELDS:
            setattr(config, k, v)
    # Bump version
    parts = config.version.split(".")
    parts[-1] = str(int(parts[-1]) + 1)
    config.version = ".".join(parts)
    config.updated_at = _utcnow()
    await db.flush()
    await _save_version(db, config_id=config.id, version=config.version, changelog="Updated")
    return {"ok": True, "version": config.version, "id": config.id}


async def delete_config(db: AsyncSession, *, config_id: str) -> dict:
    result = await db.execute(select(AgentConfig).where(AgentConfig.id == config_id))
    config = result.scalar_one_or_none()
    if config is None:
        raise MarketError(code="NOT_FOUND", message="Config not found")
    await db.delete(config)
    await db.flush()
    return {"ok": True}


async def list_configs(db: AsyncSession, *, org_id: str, visibility: str | None = None,
                       keyword: str | None = None, page: int = 1, page_size: int = 20) -> dict:
    q = select(AgentConfig).where(AgentConfig.org_id == org_id)
    if visibility:
        q = q.where(AgentConfig.visibility == visibility)
    if keyword:
        q = q.where(AgentConfig.name.ilike(f"%{keyword}%"))
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    q = q.order_by(AgentConfig.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(q)).scalars().all()
    return list_response([_config_to_dict(r) for r in rows], total, page, page_size)


async def publish_config(db: AsyncSession, *, config_id: str, visibility: str,
                         category: str = "", tags: list[str] | None = None) -> dict:
    result = await db.execute(select(AgentConfig).where(AgentConfig.id == config_id))
    config = result.scalar_one_or_none()
    if config is None:
        raise MarketError(code="NOT_FOUND", message="Config not found")
    tpl = Template(
        id=str(uuid.uuid4()), org_id=config.org_id, author_id=config.author_id,
        name=config.name, description="", category=category,
        visibility=visibility,
        config_snapshot={
            "model": config.model or {},
            "tools": config.tools or [],
            "skills": config.skills or [],
            "mcp_servers": config.mcp_servers or [],
        },
        tags=tags or [],
    )
    db.add(tpl)
    config.visibility = visibility
    await db.flush()
    return {"ok": True, "template_id": tpl.id}


async def duplicate_config(db: AsyncSession, *, config_id: str, name: str) -> dict:
    result = await db.execute(select(AgentConfig).where(AgentConfig.id == config_id))
    config = result.scalar_one_or_none()
    if config is None:
        raise MarketError(code="NOT_FOUND", message="Config not found")
    dup = AgentConfig(
        id=str(uuid.uuid4()), org_id=config.org_id, author_id=config.author_id,
        name=name, version="1.0.0",
        model=dict(config.model) if config.model else {},
        litellm_params=dict(config.litellm_params) if config.litellm_params else {},
        prompt_template=dict(config.prompt_template) if config.prompt_template else {},
        tools=list(config.tools) if config.tools else [],
        skills=list(config.skills) if config.skills else [],
        mcp_servers=list(config.mcp_servers) if config.mcp_servers else [],
        knowledge=dict(config.knowledge) if config.knowledge else {},
        memory=dict(config.memory) if config.memory else {},
        appearance=dict(config.appearance) if config.appearance else {},
        safety=dict(config.safety) if config.safety else {},
        runtime=dict(config.runtime) if config.runtime else {},
    )
    db.add(dup)
    await db.flush()
    return {"id": dup.id, "name": dup.name}


async def get_config_versions(db: AsyncSession, *, config_id: str,
                              page: int = 1, page_size: int = 20) -> dict:
    q = select(AgentConfigVersion).where(
        AgentConfigVersion.agent_config_id == config_id
    ).order_by(AgentConfigVersion.created_at.desc())
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    q = q.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(q)).scalars().all()
    items = [
        {
            "id": v.id, "version": v.version, "changelog": v.changelog,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }
        for v in rows
    ]
    return list_response(items, total, page, page_size)


def validate_config(**fields) -> dict:
    warnings = []
    errors = []
    personality = fields.get("personality", {})
    if isinstance(personality, dict):
        sp = personality.get("system_prompt", "")
        if not sp or (isinstance(sp, str) and not sp.strip()):
            errors.append("personality.system_prompt is required and cannot be empty")
    return {"valid": len(errors) == 0, "warnings": warnings, "errors": errors}


VALID_PERMISSION_MODES = {"default", "plan", "acceptEdits", "bypassPermissions"}
MAX_SYSTEM_PROMPT_LENGTH = 50000


def validate_config_full(config: dict) -> dict:
    """Comprehensive config validation with errors and warnings."""
    warnings = []
    errors = []
    personality = config.get("personality", {})
    model = config.get("model", {})
    tools = config.get("tools", {})
    permissions = config.get("permissions", {})

    # Required: system_prompt
    sp = personality.get("system_prompt", "")
    if not sp or (isinstance(sp, str) and not sp.strip()):
        errors.append("personality.system_prompt is required and cannot be empty")
    elif isinstance(sp, str) and len(sp) > MAX_SYSTEM_PROMPT_LENGTH:
        errors.append(f"personality.system_prompt exceeds {MAX_SYSTEM_PROMPT_LENGTH} characters")

    # Warnings
    if isinstance(model, dict) and not model.get("provider"):
        warnings.append("model.provider not set — default model will be used")

    # Permission mode
    if isinstance(permissions, dict):
        perm_mode = permissions.get("mode", "default")
        if perm_mode not in VALID_PERMISSION_MODES:
            errors.append(f"permissions.mode must be one of {sorted(VALID_PERMISSION_MODES)}, got '{perm_mode}'")

    return {"valid": len(errors) == 0, "warnings": warnings, "errors": errors}


def export_config(config_data: dict, format: str = "json") -> str:
    """Export config dict to JSON or YAML string, stripping internal fields."""
    exportable = {
        k: v for k, v in config_data.items()
        if k not in ("id", "created_at", "updated_at", "org_id", "author_id")
    }
    if format == "yaml":
        return yaml.dump(exportable, default_flow_style=False, allow_unicode=True)
    return json.dumps(exportable, indent=2, ensure_ascii=False)


def import_config(content: str, source: str = "json") -> dict:
    """Import config from JSON or YAML string. Returns parsed dict."""
    try:
        if source == "yaml":
            data = yaml.safe_load(content)
        else:
            data = json.loads(content)
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        raise MarketError(code="VALIDATION_ERROR", message=f"Invalid {source} content: {exc}") from exc
    if not isinstance(data, dict):
        raise MarketError(code="VALIDATION_ERROR", message="Config must be a JSON object or YAML mapping")
    return data


async def _save_version(db: AsyncSession, *, config_id: str, version: str, changelog: str = ""):
    ver = AgentConfigVersion(
        id=str(uuid.uuid4()), agent_config_id=config_id,
        version=version, config_snapshot={}, changelog=changelog,
    )
    db.add(ver)


def _config_to_dict(c: AgentConfig) -> dict:
    return {
        "id": c.id, "name": c.name, "version": c.version,
        "author_id": c.author_id, "org_id": c.org_id,
        "visibility": c.visibility or "private", "status": c.status or "draft",
        "model": c.model or {}, "litellm_params": c.litellm_params or {},
        "prompt_template": c.prompt_template or {},
        "tools": c.tools or [], "skills": c.skills or [],
        "mcp_servers": c.mcp_servers or [],
        "knowledge": c.knowledge or {}, "memory": c.memory or {},
        "appearance": c.appearance or {}, "safety": c.safety or {},
        "runtime": c.runtime or {}, "tags": c.tags or [],
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }
