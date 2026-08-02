"""Basic tracing helpers for OpenAI Agents SDK integration."""

from __future__ import annotations

from agents import RunConfig, set_tracing_disabled

from app.agent_research.config import AgentRuntimeConfig


def configure_agents_tracing(config: AgentRuntimeConfig) -> None:
    """Apply the current tracing toggle to the process-wide SDK state."""

    set_tracing_disabled(not config.tracing.enabled)


def build_run_config(
    config: AgentRuntimeConfig,
    *,
    request_id: str,
    group_id: str | None = None,
) -> RunConfig:
    """Build a reusable RunConfig for deterministic agent execution."""

    return RunConfig(
        workflow_name=config.tracing.workflow_name,
        trace_metadata={"request_id": request_id, "prompt_version": config.prompt_version},
        trace_include_sensitive_data=config.tracing.include_sensitive_data,
        tracing_disabled=not config.tracing.enabled,
        group_id=group_id,
    )
