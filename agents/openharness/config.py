"""OpenHarness adapter default configuration."""
from agent_orchestrator.contracts.adapter import AdapterConfig

DEFAULT_CONFIG = AdapterConfig(
    name="openharness",
    api_format="openai",
    base_url="https://api.deepseek.com/v1",
    default_model="deepseek-chat",
    max_tokens=4096,
    env_prefix="DS",
    extra_env={"OPENHARNESS_MAX_TOKENS": "4096"},
)
