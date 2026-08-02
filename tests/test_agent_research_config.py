"""Tests for agent runtime configuration loading."""

from __future__ import annotations

import pytest

from app.agent_research.config import AgentRuntimeConfig


def test_agent_runtime_config_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_AGENT_MODEL", "gpt-5")
    monkeypatch.setenv("OPENAI_AGENT_PROMPT_VERSION", "v9")
    monkeypatch.setenv("OPENAI_AGENT_MAX_TURNS", "8")
    monkeypatch.setenv("OPENAI_AGENT_TIMEOUT_SECONDS", "45.0")
    monkeypatch.setenv("OPENAI_AGENT_MAX_PARALLEL_AGENTS", "3")
    monkeypatch.setenv("OPENAI_AGENT_RETRY_ATTEMPTS", "2")
    monkeypatch.setenv("OPENAI_AGENT_TRACING_ENABLED", "false")
    monkeypatch.setenv("OPENAI_AGENT_WORKFLOW_NAME", "custom_workflow")
    monkeypatch.setenv("OPENAI_AGENT_TRACE_SENSITIVE_DATA", "true")

    config = AgentRuntimeConfig.from_env()

    assert config.model == "gpt-5"
    assert config.prompt_version == "v9"
    assert config.max_turns == 8
    assert config.timeout_seconds == 45.0
    assert config.max_parallel_agents == 3
    assert config.retry_attempts == 2
    assert config.tracing.enabled is False
    assert config.tracing.workflow_name == "custom_workflow"
    assert config.tracing.include_sensitive_data is True


def test_agent_runtime_config_rejects_invalid_parallelism() -> None:
    with pytest.raises(ValueError):
        AgentRuntimeConfig(max_parallel_agents=0)
