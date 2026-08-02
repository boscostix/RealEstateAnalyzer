"""Independent service wrappers for the first four specialist agents."""

from __future__ import annotations

import json
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from pydantic import BaseModel

from app.agent_research.config import AgentRuntimeConfig
from app.agent_research.context import AgentRunContext
from app.agent_research.definitions import build_specialist_agents
from app.agent_research.exceptions import (
    AgentConfigurationError,
    AgentGuardrailFailureError,
    AgentModelFailureError,
)
from app.agent_research.guardrails import validate_agent_output
from app.agent_research.orchestration_models import (
    AgentRunRecord,
    AgentRunStatus,
    AgentUsageSummary,
)
from app.agent_research.sdk import AgentRunnerProtocol, OpenAIAgentRunner
from app.agent_research.specialist_models import (
    ComparableAgentInput,
    ComparableAgentOutput,
    ListingAgentInput,
    ListingAgentOutput,
    NeighborhoodAgentInput,
    NeighborhoodAgentOutput,
    PublicRecordsAgentInput,
    PublicRecordsAgentOutput,
)
from app.agent_research.tracing import build_run_config, configure_agents_tracing
from app.agent_research.versioning import AgentName


class SpecialistAgentService[
    TInput: BaseModel,
    TOutput: ListingAgentOutput
    | PublicRecordsAgentOutput
    | ComparableAgentOutput
    | NeighborhoodAgentOutput,
]:
    """Shared execution wrapper for one independently-runnable specialist agent."""

    def __init__(
        self,
        *,
        agent_name: AgentName,
        output_type: type[TOutput],
        input_builder: Callable[[AgentRunContext], Awaitable[TInput]],
        runner: AgentRunnerProtocol | None = None,
        config: AgentRuntimeConfig | None = None,
    ) -> None:
        self._agent_name = agent_name
        self._output_type = output_type
        self._input_builder = input_builder
        self._runner = runner or OpenAIAgentRunner()
        self._config = config or AgentRuntimeConfig.from_env()

    async def run(self, context: AgentRunContext) -> TOutput:
        run_result = await self.run_with_record(context)
        if run_result.output is None:
            raise AgentModelFailureError(
                message=run_result.record.error_message or "Agent run failed."
            )
        return run_result.output

    async def run_with_record(self, context: AgentRunContext) -> ServiceRunResult[TOutput]:
        if not context.request_id:
            raise AgentConfigurationError(message="request_id is required for agent execution.")

        configure_agents_tracing(self._config)
        started_perf = time.perf_counter()
        started_at = datetime.now(UTC)
        built_input = await self._input_builder(context)
        agents = build_specialist_agents(self._config.model)
        agent = agents[self._agent_name]
        run_config = build_run_config(
            self._config,
            request_id=context.request_id,
            group_id=context.analysis_id,
        )
        agent_input = json.dumps(
            built_input.model_dump(mode="json"),
            separators=(",", ":"),
        )
        try:
            artifacts = await self._runner.run_detailed(
                agent=agent,
                agent_input=agent_input,
                context=context,
                run_config=run_config,
                output_type=self._output_type,
            )
            validate_agent_output(
                agent_name=self._agent_name,
                output=artifacts.output,
                context=context,
            )
            return ServiceRunResult(
                output=artifacts.output,
                record=AgentRunRecord(
                    agent_name=self._agent_name,
                    status=AgentRunStatus.COMPLETED,
                    started_at=started_at,
                    completed_at=datetime.now(UTC),
                    duration_ms=int((time.perf_counter() - started_perf) * 1000),
                    output_available=True,
                    usage=AgentUsageSummary(
                        requests=artifacts.usage.requests,
                        input_tokens=artifacts.usage.input_tokens,
                        output_tokens=artifacts.usage.output_tokens,
                        total_tokens=artifacts.usage.total_tokens,
                    ),
                    trace_metadata={
                        "request_id": context.request_id,
                        "analysis_id": context.analysis_id or "",
                        "prompt_version": context.agent_config.prompt_version,
                    },
                ),
            )
        except AgentGuardrailFailureError:
            raise
        except Exception as exc:
            raise AgentModelFailureError(message=str(exc)) from exc


class ServiceRunResult[TOutput]:
    """Specialist-agent service result with an explicit run record."""

    def __init__(self, *, output: TOutput | None, record: AgentRunRecord) -> None:
        self.output = output
        self.record = record


class ListingAgentService(SpecialistAgentService[ListingAgentInput, ListingAgentOutput]):
    def __init__(
        self,
        *,
        runner: AgentRunnerProtocol | None = None,
        config: AgentRuntimeConfig | None = None,
    ) -> None:
        from app.agent_research.input_builders import build_listing_agent_input

        super().__init__(
            agent_name=AgentName.LISTING,
            output_type=ListingAgentOutput,
            input_builder=build_listing_agent_input,
            runner=runner,
            config=config,
        )


class PublicRecordsAgentService(
    SpecialistAgentService[PublicRecordsAgentInput, PublicRecordsAgentOutput]
):
    def __init__(
        self,
        *,
        runner: AgentRunnerProtocol | None = None,
        config: AgentRuntimeConfig | None = None,
    ) -> None:
        from app.agent_research.input_builders import build_public_records_agent_input

        super().__init__(
            agent_name=AgentName.PUBLIC_RECORDS,
            output_type=PublicRecordsAgentOutput,
            input_builder=build_public_records_agent_input,
            runner=runner,
            config=config,
        )


class ComparableAgentService(SpecialistAgentService[ComparableAgentInput, ComparableAgentOutput]):
    def __init__(
        self,
        *,
        runner: AgentRunnerProtocol | None = None,
        config: AgentRuntimeConfig | None = None,
    ) -> None:
        from app.agent_research.input_builders import build_comparable_agent_input

        super().__init__(
            agent_name=AgentName.COMPARABLE,
            output_type=ComparableAgentOutput,
            input_builder=build_comparable_agent_input,
            runner=runner,
            config=config,
        )


class NeighborhoodAgentService(
    SpecialistAgentService[NeighborhoodAgentInput, NeighborhoodAgentOutput]
):
    def __init__(
        self,
        *,
        runner: AgentRunnerProtocol | None = None,
        config: AgentRuntimeConfig | None = None,
    ) -> None:
        from app.agent_research.input_builders import build_neighborhood_agent_input

        super().__init__(
            agent_name=AgentName.NEIGHBORHOOD,
            output_type=NeighborhoodAgentOutput,
            input_builder=build_neighborhood_agent_input,
            runner=runner,
            config=config,
        )
