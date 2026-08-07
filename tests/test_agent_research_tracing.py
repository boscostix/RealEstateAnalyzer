"""Tests for basic tracing helpers."""

from __future__ import annotations

import pytest
from agents.run_context import AgentHookContext, RunContextWrapper

from app.agent_research.config import AgentRuntimeConfig, AgentTracingConfig
from app.agent_research.tracing import (
    build_run_config,
    build_run_hooks,
    configure_agents_tracing,
)
from app.agent_research.versioning import AgentName
from tests.agent_sdk_utils import make_agent_context


def test_build_run_config_reflects_runtime_settings() -> None:
    config = AgentRuntimeConfig()

    run_config = build_run_config(
        config,
        request_id="req-123",
        group_id="analysis-1",
        agent_name=str(AgentName.LISTING),
        agent_version="listing_agent:v1",
        prompt_version="v1",
    )

    assert run_config.workflow_name == config.tracing.workflow_name
    assert run_config.group_id == "analysis-1"
    assert run_config.trace_metadata == {
        "request_id": "req-123",
        "workflow_name": config.tracing.workflow_name,
        "prompt_version": "v1",
        "trace_sensitive_data": "false",
        "analysis_id": "analysis-1",
        "agent_name": "listing_agent",
        "agent_version": "listing_agent:v1",
    }
    assert run_config.tracing_disabled is False
    assert run_config.trace_include_sensitive_data is False


def test_configure_agents_tracing_sets_sdk_toggle(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[bool] = []

    def fake_set_tracing_disabled(value: bool) -> None:
        calls.append(value)

    monkeypatch.setattr(
        "app.agent_research.tracing.set_tracing_disabled", fake_set_tracing_disabled
    )

    configure_agents_tracing(AgentRuntimeConfig())
    configure_agents_tracing(
        AgentRuntimeConfig(
            tracing=AgentTracingConfig(enabled=False, workflow_name="x"),
        )
    )

    assert calls == [False, True]


@pytest.mark.asyncio
async def test_build_run_hooks_collects_agent_and_tool_lifecycle_events() -> None:
    context = make_agent_context()
    hooks = build_run_hooks(
        context.agent_config,
        request_id=context.request_id,
        analysis_id=context.analysis_id,
        agent_name=str(AgentName.LISTING),
        agent_version="listing_agent:v1",
        prompt_version="v1",
    )
    run_context = RunContextWrapper(context)
    hook_context = AgentHookContext(context)

    class StubAgent:
        name = "listing_agent"

    class StubTool:
        name = "get_listing_snapshot"

    await hooks.on_agent_start(hook_context, StubAgent())
    await hooks.on_llm_start(run_context, StubAgent(), "system", [])
    await hooks.on_tool_start(run_context, StubAgent(), StubTool())
    await hooks.on_handoff(run_context, StubAgent(), StubAgent())
    await hooks.on_agent_end(hook_context, StubAgent(), {"ok": True})

    assert hooks.summary.agent_start_count == 1
    assert hooks.summary.agent_end_count == 1
    assert hooks.summary.llm_call_count == 1
    assert hooks.summary.tool_call_count == 1
    assert hooks.summary.handoff_count == 1
    assert hooks.summary.tool_names == ["get_listing_snapshot"]
