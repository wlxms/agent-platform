"""API-to-SDK request mapping layer.

Converts external API requests (api-protocol.md format) to SDK requests
(agent_orchestrator.contracts.models.InstanceCreateRequest).
"""
import uuid
from pathlib import Path

from pydantic import BaseModel, Field


class CreateAgentRequest(BaseModel):
    """External API request for creating an agent (matches api-protocol.md)."""

    name: str
    template_id: str | None = None
    agent_config_id: str | None = None
    model: str | None = None
    config: dict | None = None


class AgentMappingSettings(BaseModel):
    """Configuration for the API-to-SDK mapping."""

    workspace_base: str = "/tmp/ohent/workspaces"
    templates_base: str = "/tmp/ohent/templates"
    default_template_id: str = "default"
    allowed_roots: list[str] = Field(default_factory=lambda: ["/tmp/ohent"])


class InstanceMapper:
    """Maps external API requests to SDK InstanceCreateRequest."""

    def __init__(self, settings: AgentMappingSettings | None = None):
        self.settings = settings or AgentMappingSettings()
        Path(self.settings.templates_base).mkdir(parents=True, exist_ok=True)
        Path(self.settings.workspace_base).mkdir(parents=True, exist_ok=True)
        default_tmpl = Path(self.settings.templates_base) / self.settings.default_template_id
        default_tmpl.mkdir(exist_ok=True)
        if not any(default_tmpl.iterdir()):
            (default_tmpl / ".keep").write_text("")

    def map_create_request(self, req: CreateAgentRequest) -> tuple:
        """Convert CreateAgentRequest to SDK InstanceCreateRequest params.

        Returns: (workspace_root, template_id, seed_config)
        """
        from agent_orchestrator.contracts.models import SeedConfig

        instance_id = str(uuid.uuid4())[:8]
        workspace_root = str(Path(self.settings.workspace_base) / f"{req.name}-{instance_id}")
        Path(workspace_root).mkdir(parents=True, exist_ok=True)

        template_id = req.template_id or self.settings.default_template_id
        template_dir = str(Path(self.settings.templates_base) / template_id)
        Path(template_dir).mkdir(parents=True, exist_ok=True)

        seed = SeedConfig(
            mode="merge",
            template_dir=template_dir,
        )

        return workspace_root, template_id, seed

    def to_sdk_request(self, req: CreateAgentRequest):
        """Full conversion to SDK InstanceCreateRequest."""
        from agent_orchestrator.contracts.models import InstanceCreateRequest

        workspace_root, template_id, seed = self.map_create_request(req)

        return InstanceCreateRequest(
            name=req.name,
            host="local",
            template_id=template_id,
            workspace_root=workspace_root,
            seed=seed,
        )
