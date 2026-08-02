"""Thin, mockable wrapper around the OpenAI Agents SDK runner."""

from __future__ import annotations

from typing import Protocol, TypeVar

from agents import Agent, Runner
from agents.run_config import RunConfig

from app.agent_research.context import AgentRunContext
from app.agent_research.exceptions import InvalidStructuredAgentOutputError

TOutput = TypeVar("TOutput")


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
        result = await Runner.run(
            agent,
            agent_input,
            context=context,
            max_turns=context.agent_config.max_turns,
            run_config=run_config,
        )
        try:
            return result.final_output_as(output_type)
        except Exception as exc:  # pragma: no cover - defensive SDK adaptation
            raise InvalidStructuredAgentOutputError(
                message="The agent run did not return the expected structured output.",
            ) from exc
