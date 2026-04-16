"""OpenHarness agent adapter implementation.

Translates orchestrator requests into OpenHarness CLI (oh) invocations.
"""
from __future__ import annotations

from agent_orchestrator.contracts.adapter import AdapterConfig

from .config import DEFAULT_CONFIG


class OpenHarnessAdapter:
    """Adapter for the OpenHarness CLI agent runtime."""

    def __init__(self, config: AdapterConfig | None = None) -> None:
        self._config = config or DEFAULT_CONFIG

    @property
    def name(self) -> str:
        return self._config.name

    @property
    def config(self) -> AdapterConfig:
        return self._config

    def build_exec_argv(
        self,
        prompt: str,
        model: str,
        api_key: str = "",
        *,
        api_format: str = "",
        base_url: str = "",
        output_format: str = "text",
        max_tokens: int = 0,
    ) -> list[str]:
        resolved_format = api_format or self._config.api_format
        resolved_base_url = base_url or self._config.base_url
        return [
            "oh",
            "--api-format", resolved_format,
            "--base-url", resolved_base_url,
            "--model", model,
            "-k", api_key,
            "-p", prompt,
            "--output-format", output_format,
        ]

    def build_exec_env(self, api_key: str, max_tokens: int = 0) -> dict[str, str]:
        resolved_tokens = max_tokens or self._config.max_tokens
        env: dict[str, str] = {
            f"{self._config.env_prefix}_API_KEY": api_key,
        }
        env.update(self._config.extra_env)
        if "OPENHARNESS_MAX_TOKENS" in env:
            env["OPENHARNESS_MAX_TOKENS"] = str(resolved_tokens)
        return env
