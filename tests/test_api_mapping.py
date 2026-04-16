import pytest
import tempfile
import shutil
from pathlib import Path


class TestInstanceMapper:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp(prefix="ohent-map-test-")

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_map_create_request_defaults(self):
        from ohent_shared.api_mapping import InstanceMapper, CreateAgentRequest, AgentMappingSettings

        settings = AgentMappingSettings(
            workspace_base=f"{self.temp_dir}/workspaces",
            templates_base=f"{self.temp_dir}/templates",
            allowed_roots=[self.temp_dir],
        )
        mapper = InstanceMapper(settings=settings)
        req = CreateAgentRequest(name="test-agent")

        workspace_root, template_id, seed = mapper.map_create_request(req)

        assert self.temp_dir in workspace_root
        assert "test-agent" in workspace_root
        assert template_id == "default"
        assert seed.mode == "merge"
        assert Path(seed.template_dir).exists()

    def test_map_create_request_with_template(self):
        from ohent_shared.api_mapping import InstanceMapper, CreateAgentRequest, AgentMappingSettings

        custom_tmpl = Path(self.temp_dir) / "templates" / "python-dev"
        custom_tmpl.mkdir(parents=True)
        (custom_tmpl / "setup.py").write_text("# setup")

        settings = AgentMappingSettings(
            workspace_base=f"{self.temp_dir}/workspaces",
            templates_base=f"{self.temp_dir}/templates",
            allowed_roots=[self.temp_dir],
        )
        mapper = InstanceMapper(settings=settings)
        req = CreateAgentRequest(name="py-agent", template_id="python-dev")

        workspace_root, template_id, seed = mapper.map_create_request(req)

        assert template_id == "python-dev"
        assert seed.template_dir == str(custom_tmpl)

    def test_to_sdk_request(self):
        from ohent_shared.api_mapping import InstanceMapper, CreateAgentRequest, AgentMappingSettings

        settings = AgentMappingSettings(
            workspace_base=f"{self.temp_dir}/workspaces",
            templates_base=f"{self.temp_dir}/templates",
            allowed_roots=[self.temp_dir],
        )
        mapper = InstanceMapper(settings=settings)
        req = CreateAgentRequest(name="sdk-test")

        sdk_req = mapper.to_sdk_request(req)

        assert sdk_req.name == "sdk-test"
        assert sdk_req.host == "local"
        assert sdk_req.template_id == "default"
        assert sdk_req.workspace_root
        assert sdk_req.seed.template_dir

    def test_creates_default_template_on_init(self):
        from ohent_shared.api_mapping import InstanceMapper, AgentMappingSettings

        settings = AgentMappingSettings(
            workspace_base=f"{self.temp_dir}/workspaces",
            templates_base=f"{self.temp_dir}/templates",
            allowed_roots=[self.temp_dir],
        )
        mapper = InstanceMapper(settings=settings)

        default_tmpl = Path(self.temp_dir) / "templates" / "default"
        assert default_tmpl.exists()
        assert any(default_tmpl.iterdir())

    def test_creates_workspace_dir(self):
        from ohent_shared.api_mapping import InstanceMapper, CreateAgentRequest, AgentMappingSettings

        settings = AgentMappingSettings(
            workspace_base=f"{self.temp_dir}/workspaces",
            templates_base=f"{self.temp_dir}/templates",
            allowed_roots=[self.temp_dir],
        )
        mapper = InstanceMapper(settings=settings)
        req = CreateAgentRequest(name="ws-test")

        workspace_root, _, _ = mapper.map_create_request(req)
        assert Path(workspace_root).exists()
        assert Path(workspace_root).is_dir()

    def test_end_to_end_with_sdk(self):
        from ohent_shared.api_mapping import InstanceMapper, CreateAgentRequest, AgentMappingSettings
        from agent_orchestrator import OrchestratorClient

        settings = AgentMappingSettings(
            workspace_base=f"{self.temp_dir}/workspaces",
            templates_base=f"{self.temp_dir}/templates",
            allowed_roots=[self.temp_dir],
        )
        mapper = InstanceMapper(settings=settings)
        req = CreateAgentRequest(name="e2e-test")

        sdk_req = mapper.to_sdk_request(req)

        client = OrchestratorClient(
            allowed_roots=[self.temp_dir],
            runtime="noop",
            db_path=":memory:",
        )

        record = client.create_instance(sdk_req)
        assert record.status in ("ready", "running", "seeding")
        assert record.name == "e2e-test"
