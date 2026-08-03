"""Thin, mockable wrapper around the OpenAI Agents SDK for committee runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, TypeVar

from agents import Agent, Runner
from agents.run_config import RunConfig
from agents.usage import Usage

from app.investment_committee.context import CommitteeRunContext
from app.investment_committee.exceptions import InvalidCommitteeStructuredOutputError

TOutput = TypeVar("TOutput")


@dataclass(slots=True)
class CommitteeRunArtifacts[TOutput]:
    output: TOutput
    usage: Usage = field(default_factory=Usage)
    response_count: int = 0


class CommitteeRunnerProtocol(Protocol):
    async def run(
        self,
        *,
        agent: Agent[CommitteeRunContext],
        agent_input: str,
        context: CommitteeRunContext,
        run_config: RunConfig,
        output_type: type[TOutput],
    ) -> TOutput: ...

    async def run_detailed(
        self,
        *,
        agent: Agent[CommitteeRunContext],
        agent_input: str,
        context: CommitteeRunContext,
        run_config: RunConfig,
        output_type: type[TOutput],
    ) -> CommitteeRunArtifacts[TOutput]: ...


class OpenAICommitteeRunner:
    async def run(
        self,
        *,
        agent: Agent[CommitteeRunContext],
        agent_input: str,
        context: CommitteeRunContext,
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
        agent: Agent[CommitteeRunContext],
        agent_input: str,
        context: CommitteeRunContext,
        run_config: RunConfig,
        output_type: type[TOutput],
    ) -> CommitteeRunArtifacts[TOutput]:
        result = await Runner.run(
            agent,
            agent_input,
            context=context,
            max_turns=context.committee_config.max_turns,
            run_config=run_config,
        )
        try:
            output = result.final_output_as(output_type)
        except Exception as exc:  # pragma: no cover
            raise InvalidCommitteeStructuredOutputError(
                message="The investment committee did not return the expected structured output."
            ) from exc
        usage = Usage()
        raw_responses = getattr(result, "raw_responses", ())
        for response in raw_responses:
            usage.add(response.usage)
        return CommitteeRunArtifacts(
            output=output,
            usage=usage,
            response_count=len(raw_responses),
        )
