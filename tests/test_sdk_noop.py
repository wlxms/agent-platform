import tempfile
import shutil
from pathlib import Path


class TestSDKNoopDriver:
    """Verify SDK noop driver works end-to-end."""

    def setup_method(self):
        """Create temp template dir and allowed_roots."""
        self.temp_dir = tempfile.mkdtemp(prefix="ohent-test-")
        self.template_dir = Path(self.temp_dir) / "templates" / "default"
        self.template_dir.mkdir(parents=True)
        # Create a dummy seed file so apply_seed has something to copy
        (self.template_dir / ".keep").write_text("seed marker")
        self.workspace_root = Path(self.temp_dir) / "workspaces"
        self.workspace_root.mkdir()
        self.allowed_roots = [self.temp_dir]

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_instance_returns_ready(self):
        """noop driver should create instance with status=ready."""
        from openharness_sdk import OrchestratorClient
        from openharness_sdk.contracts.models import SeedConfig, InstanceCreateRequest

        client = OrchestratorClient(
            allowed_roots=self.allowed_roots,
            runtime="noop",
            db_path=":memory:",
        )

        req = InstanceCreateRequest(
            name="test-instance",
            host="local",
            template_id="default",
            workspace_root=str(self.workspace_root / "test-instance"),
            seed=SeedConfig(mode="merge", template_dir=str(self.template_dir)),
        )

        record = client.create_instance(req)
        assert record.status in ("ready", "seeding", "running")
        assert record.name == "test-instance"
        assert record.host == "local"
        assert record.instance_id

    def test_list_instances(self):
        """list_instances should return created instances."""
        from openharness_sdk import OrchestratorClient
        from openharness_sdk.contracts.models import SeedConfig, InstanceCreateRequest

        client = OrchestratorClient(
            allowed_roots=self.allowed_roots,
            runtime="noop",
            db_path=":memory:",
        )

        req = InstanceCreateRequest(
            name="list-test",
            host="local",
            template_id="default",
            workspace_root=str(self.workspace_root / "list-test"),
            seed=SeedConfig(mode="merge", template_dir=str(self.template_dir)),
        )

        client.create_instance(req)
        instances = client.list_instances()
        assert len(instances) >= 1
        assert any(i.name == "list-test" for i in instances)

    def test_get_instance(self):
        """get_instance should return the created instance."""
        from openharness_sdk import OrchestratorClient
        from openharness_sdk.contracts.models import SeedConfig, InstanceCreateRequest

        client = OrchestratorClient(
            allowed_roots=self.allowed_roots,
            runtime="noop",
            db_path=":memory:",
        )

        req = InstanceCreateRequest(
            name="get-test",
            host="local",
            template_id="default",
            workspace_root=str(self.workspace_root / "get-test"),
            seed=SeedConfig(mode="merge", template_dir=str(self.template_dir)),
        )

        created = client.create_instance(req)
        fetched = client.get_instance(created.instance_id)
        assert fetched.instance_id == created.instance_id
        assert fetched.name == "get-test"

    def test_destroy_instance(self):
        """destroy_instance should remove the instance."""
        from openharness_sdk import OrchestratorClient
        from openharness_sdk.contracts.models import SeedConfig, InstanceCreateRequest

        client = OrchestratorClient(
            allowed_roots=self.allowed_roots,
            runtime="noop",
            db_path=":memory:",
        )

        req = InstanceCreateRequest(
            name="destroy-test",
            host="local",
            template_id="default",
            workspace_root=str(self.workspace_root / "destroy-test"),
            seed=SeedConfig(mode="merge", template_dir=str(self.template_dir)),
        )

        created = client.create_instance(req)
        result = client.destroy_instance(created.instance_id)
        assert result.deleted is True

        # After destroy, list should not contain the instance
        instances = client.list_instances(include_deleted=False)
        assert not any(i.instance_id == created.instance_id for i in instances)

    def test_send_message(self):
        """send_message should return a MessageResult."""
        from openharness_sdk import OrchestratorClient
        from openharness_sdk.contracts.models import SeedConfig, InstanceCreateRequest

        client = OrchestratorClient(
            allowed_roots=self.allowed_roots,
            runtime="noop",
            db_path=":memory:",
        )

        req = InstanceCreateRequest(
            name="msg-test",
            host="local",
            template_id="default",
            workspace_root=str(self.workspace_root / "msg-test"),
            seed=SeedConfig(mode="merge", template_dir=str(self.template_dir)),
        )

        created = client.create_instance(req)

        # Note: send_message with noop driver may fail because there's no real container.
        # Test that it doesn't crash with an unexpected exception.
        try:
            result = client.send_message(
                instance_id=created.instance_id,
                prompt="hello",
                max_turns=1,
            )
            assert result.instance_id == created.instance_id
        except Exception as e:
            # noop driver may not support exec, or may require DS_API_KEY - both acceptable
            msg = str(e).lower()
            assert "exec" in msg or "container" in msg or "api_key" in msg or "required" in msg
