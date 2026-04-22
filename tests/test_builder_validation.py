"""Tests for Builder config validation (T2.4)."""


def test_validate_complete_config():
    from agentp_market.service import validate_config_full
    config = {
        "personality": {"system_prompt": "You are helpful"},
        "model": {"provider": "litellm", "litellm_params": {"model": "openai/gpt-4o"}},
        "tools": {"allowed": ["Read"]},
        "permissions": {"mode": "default"},
    }
    result = validate_config_full(config)
    assert result["valid"] is True
    assert len(result["errors"]) == 0


def test_validate_missing_system_prompt():
    from agentp_market.service import validate_config_full
    config = {"personality": {}, "model": {}}
    result = validate_config_full(config)
    assert result["valid"] is False
    assert any("system_prompt" in e for e in result["errors"])


def test_validate_invalid_permission_mode():
    from agentp_market.service import validate_config_full
    config = {"personality": {"system_prompt": "Hi"}, "permissions": {"mode": "superuser"}}
    result = validate_config_full(config)
    assert result["valid"] is False
    assert any("permission" in e.lower() for e in result["errors"])


def test_validate_warns_no_model():
    from agentp_market.service import validate_config_full
    config = {"personality": {"system_prompt": "Hi"}, "model": {}}
    result = validate_config_full(config)
    assert result["valid"] is True
    assert len(result["warnings"]) > 0
