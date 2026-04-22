"""Tests for Builder config import/export (T2.3)."""
import json

import pytest
import yaml


def test_export_config_to_json():
    from agentp_market.service import export_config
    config_data = {"name": "Export Test", "model": {"provider": "litellm"}}
    result = export_config(config_data, format="json")
    parsed = json.loads(result)
    assert parsed["name"] == "Export Test"


def test_export_config_to_yaml():
    from agentp_market.service import export_config
    config_data = {"name": "YAML Export", "model": {"provider": "litellm"}}
    result = export_config(config_data, format="yaml")
    parsed = yaml.safe_load(result)
    assert parsed["name"] == "YAML Export"


def test_import_config_from_json():
    from agentp_market.service import import_config
    json_str = '{"name": "JSON Import", "model": {"provider": "litellm"}}'
    result = import_config(json_str, source="json")
    assert result["name"] == "JSON Import"


def test_import_config_from_yaml():
    from agentp_market.service import import_config
    yaml_str = "name: YAML Import\nmodel:\n  provider: litellm"
    result = import_config(yaml_str, source="yaml")
    assert result["name"] == "YAML Import"


def test_import_config_invalid_json():
    from agentp_market.service import import_config, MarketError
    with pytest.raises(MarketError):
        import_config("{invalid json", source="json")
