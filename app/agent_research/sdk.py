"""Thin, mockable wrapper around the OpenAI Agents SDK runner."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, TypeVar

from agents import Agent, Runner
from agents.run_config import RunConfig
from agents.usage import Usage

from app.agent_research.context import AgentRunContext
from app.agent_research.exceptions import InvalidStructuredAgentOutputError

TOutput = TypeVar("TOutput")


@dataclass(slots=True)
class AgentRunArtifacts[TOutput]:
    """Structured runner artifacts used by higher-level orchestration."""

    output: TOutput
    usage: Usage = field(default_factory=Usage)
    response_count: int = 0


class AgentRunnerProtocol(Protocol):
    """Protocol used to mock agent runs in tests."""

    async def run(
        self,
        *,
        agent: Agent[AgentRunContext],
        agent_input: str,
        context: AgentRunContext,
        run_config: RunConfig,
        output_type: type[TOutput],
    ) -> TOutput:
        """Execute one agent and return a validated structured output."""

    async def run_detailed(
        self,
        *,
        agent: Agent[AgentRunContext],
        agent_input: str,
        context: AgentRunContext,
        run_config: RunConfig,
        output_type: type[TOutput],
    ) -> AgentRunArtifacts[TOutput]:
        """Execute one agent and return structured output plus runner metadata."""


class OpenAIAgentRunner:
    """Project-local adapter for `Runner.run`."""

    async def run(
        self,
        *,
        agent: Agent[AgentRunContext],
        agent_input: str,
        context: AgentRunContext,
        run_config: RunConfig,
        output_type: type[TOutput],
    ) -> TOutput:
        artifacts = await self.run_detailed(
            agent=agent,
            agent_input=agent_input,
            context=context,
            run_config=run_config,
            output_type=output_type,
        )
        return artifacts.output

    async def run_detailed(
        self,
        *,
        agent: Agent[AgentRunContext],
        agent_input: str,
        context: AgentRunContext,
        run_config: RunConfig,
        output_type: type[TOutput],
    ) -> AgentRunArtifacts[TOutput]:
        result = await Runner.run(
            agent,
            agent_input,
            context=context,
            max_turns=context.agent_config.max_turns,
            run_config=run_config,
        )
        try:
            output = result.final_output_as(output_type)
        except Exception as exc:  # pragma: no cover - defensive SDK adaptation
            raise InvalidStructuredAgentOutputError(
                message="The agent run did not return the expected structured output.",
            ) from exc
        usage = Usage()
        raw_responses = getattr(result, "raw_responses", ())
        for response in raw_responses:
            usage.add(response.usage)
        return AgentRunArtifacts(
            output=output,
            usage=usage,
            response_count=len(raw_responses),
        )
