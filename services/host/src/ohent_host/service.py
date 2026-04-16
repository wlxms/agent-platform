import tempfile
from pathlib import Path

from openharness_sdk import OrchestratorClient
from ohent_shared.api_mapping import AgentMappingSettings, CreateAgentRequest, InstanceMapper


class HostService:
    def __init__(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="ohent-host-")
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

    def create_instance(self, req: CreateAgentRequest) -> dict:
        sdk_req = self.mapper.to_sdk_request(req)
        record = self.client.create_instance(sdk_req)
        return _record_to_dict(record)

    def list_instances(self) -> dict:
        instances = self.client.list_instances()
        return {
            "items": [_record_to_dict(r) for r in instances],
            "total": len(instances),
            "page": 1,
            "page_size": 20,
        }

    def get_instance(self, instance_id: str) -> dict:
        record = self.client.get_instance(instance_id)
        return {"data": _record_to_dict(record)}

    def destroy_instance(self, instance_id: str) -> dict:
        result = self.client.destroy_instance(instance_id)
        return {"ok": True, "deleted": result.deleted}

    def send_message(self, instance_id: str, prompt: str, model: str | None = None) -> dict:
        try:
            result = self.client.send_message(
                instance_id=instance_id,
                prompt=prompt,
                model=model,
                max_turns=1,
            )
            return {"data": {
                "instance_id": result.instance_id,
                "reply_text": result.reply_text,
                "model": result.model,
            }}
        except Exception as e:
            raise RuntimeError(f"Message failed: {e}") from e


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
