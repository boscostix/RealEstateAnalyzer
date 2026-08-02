"""Tests for basic tracing helpers."""

from __future__ import annotations

import pytest

from app.agent_research.config import AgentRuntimeConfig
from app.agent_research.tracing import build_run_config, configure_agents_tracing


def test_build_run_config_reflects_runtime_settings() -> None:
    config = AgentRuntimeConfig()

    run_config = build_run_config(config, request_id="req-123", group_id="analysis-1")

    assert run_config.workflow_name == config.tracing.workflow_name
    assert run_config.group_id == "analysis-1"
    assert run_config.trace_metadata == {
        "request_id": "req-123",
        "prompt_version": config.prompt_version,
    }
    assert run_config.tracing_disabled is False


def test_configure_agents_tracing_sets_sdk_toggle(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[bool] = []

    def fake_set_tracing_disabled(value: bool) -> None:
        calls.append(value)

    monkeypatch.setattr(
        "app.agent_research.tracing.set_tracing_disabled", fake_set_tracing_disabled
    )

    configure_agents_tracing(AgentRuntimeConfig())
    configure_agents_tracing(AgentRuntimeConfig(tracing={"enabled": False, "workflow_name": "x"}))

    assert calls == [False, True]
