"""Tracing helpers and lifecycle hooks for OpenAI Agents SDK integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agents import RunConfig, RunHooks, set_tracing_disabled
from agents.run_context import AgentHookContext, RunContextWrapper

from app.agent_research.config import AgentRuntimeConfig
from app.agent_research.context import AgentRunContext


def configure_agents_tracing(config: AgentRuntimeConfig) -> None:
    """Apply the current tracing toggle to the process-wide SDK state."""

    set_tracing_disabled(not config.tracing.enabled)


@dataclass(slots=True)
class AgentLifecycleSummary:
    """Trace-safe summary of one agent run's lifecycle events."""

    workflow_name: str
    agent_name: str
    agent_version: str
    prompt_version: str
    request_id: str
    analysis_id: str | None
    trace_enabled: bool
    include_sensitive_data: bool
    agent_start_count: int = 0
    agent_end_count: int = 0
    llm_call_count: int = 0
    tool_call_count: int = 0
    handoff_count: int = 0
    tool_names: list[str] = field(default_factory=list)
    handoff_targets: list[str] = field(default_factory=list)


class AgentLifecycleHooks(RunHooks[AgentRunContext]):
    """Collect lifecycle events without exposing sensitive inputs by default."""

    def __init__(
        self,
        *,
        config: AgentRuntimeConfig,
        agent_name: str,
        agent_version: str,
        prompt_version: str,
        request_id: str,
        analysis_id: str | None,
    ) -> None:
        self._summary = AgentLifecycleSummary(
            workflow_name=config.tracing.workflow_name,
            agent_name=agent_name,
            agent_version=agent_version,
            prompt_version=prompt_version,
            request_id=request_id,
            analysis_id=analysis_id,
            trace_enabled=config.tracing.enabled,
            include_sensitive_data=config.tracing.include_sensitive_data,
        )

    @property
    def summary(self) -> AgentLifecycleSummary:
        return self._summary

    async def on_llm_start(
        self,
        context: RunContextWrapper[AgentRunContext],
        agent: Any,
        system_prompt: str | None,
        input_items: list[Any],
    ) -> None:
        del context, agent, system_prompt, input_items
        self._summary.llm_call_count += 1

    async def on_agent_start(
        self,
        context: AgentHookContext[AgentRunContext],
        agent: Any,
    ) -> None:
        del context, agent
        self._summary.agent_start_count += 1

    async def on_agent_end(
        self,
        context: AgentHookContext[AgentRunContext],
        agent: Any,
        output: Any,
    ) -> None:
        del context, agent, output
        self._summary.agent_end_count += 1

    async def on_handoff(
        self,
        context: RunContextWrapper[AgentRunContext],
        from_agent: Any,
        to_agent: Any,
    ) -> None:
        del context, from_agent
        self._summary.handoff_count += 1
        self._summary.handoff_targets.append(str(getattr(to_agent, "name", "unknown")))

    async def on_tool_start(
        self,
        context: RunContextWrapper[AgentRunContext],
        agent: Any,
        tool: Any,
    ) -> None:
        del context, agent
        self._summary.tool_call_count += 1
        self._summary.tool_names.append(str(getattr(tool, "name", "unknown_tool")))


def build_trace_metadata(
    config: AgentRuntimeConfig,
    *,
    request_id: str,
    group_id: str | None = None,
    agent_name: str | None = None,
    agent_version: str | None = None,
    prompt_version: str | None = None,
) -> dict[str, str]:
    """Build stable trace metadata for one run without leaking payload contents."""

    metadata = {
        "request_id": request_id,
        "workflow_name": config.tracing.workflow_name,
        "prompt_version": prompt_version or config.prompt_version,
        "trace_sensitive_data": str(config.tracing.include_sensitive_data).lower(),
    }
    if group_id is not None:
        metadata["analysis_id"] = group_id
    if agent_name is not None:
        metadata["agent_name"] = agent_name
    if agent_version is not None:
        metadata["agent_version"] = agent_version
    return metadata


def build_run_hooks(
    config: AgentRuntimeConfig,
    *,
    request_id: str,
    analysis_id: str | None,
    agent_name: str,
    agent_version: str,
    prompt_version: str,
) -> AgentLifecycleHooks:
    """Create lifecycle hooks for one agent run."""

    return AgentLifecycleHooks(
        config=config,
        agent_name=agent_name,
        agent_version=agent_version,
        prompt_version=prompt_version,
        request_id=request_id,
        analysis_id=analysis_id,
    )


def build_run_config(
    config: AgentRuntimeConfig,
    *,
    request_id: str,
    group_id: str | None = None,
    agent_name: str | None = None,
    agent_version: str | None = None,
    prompt_version: str | None = None,
) -> RunConfig:
    """Build a reusable RunConfig for deterministic agent execution."""

    return RunConfig(
        workflow_name=config.tracing.workflow_name,
        trace_metadata=build_trace_metadata(
            config,
            request_id=request_id,
            group_id=group_id,
            agent_name=agent_name,
            agent_version=agent_version,
            prompt_version=prompt_version,
        ),
        trace_include_sensitive_data=config.tracing.include_sensitive_data,
        tracing_disabled=not config.tracing.enabled,
        group_id=group_id,
    )
