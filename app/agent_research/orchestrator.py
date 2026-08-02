"""Deterministic parallel orchestrator for the first four specialist agents."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable
from datetime import UTC, datetime
from typing import Any, Protocol, cast

from app.agent_research.config import AgentRuntimeConfig
from app.agent_research.context import AgentRunContext
from app.agent_research.exceptions import (
    AgentResearchError,
    AgentTimeoutError,
    WorkflowTimeoutError,
)
from app.agent_research.orchestration_models import (
    AgentRunRecord,
    AgentRunStatus,
    AgentUsageSummary,
    SpecialistWorkflowMetadata,
    SpecialistWorkflowResponse,
    SpecialistWorkflowResult,
    WorkflowStatus,
)
from app.agent_research.services import (
    ComparableAgentService,
    ListingAgentService,
    NeighborhoodAgentService,
    PublicRecordsAgentService,
)
from app.agent_research.specialist_models import (
    ComparableAgentOutput,
    ListingAgentOutput,
    NeighborhoodAgentOutput,
    PublicRecordsAgentOutput,
)
from app.agent_research.versioning import AgentName

logger = logging.getLogger("real_estate_analyzer.agent_orchestrator")


class RunWithRecordService(Protocol):
    """Protocol for independently-runnable specialist-agent services."""

    def run_with_record(self, context: AgentRunContext) -> Awaitable[Any]:
        """Execute one specialist agent and return its typed result plus run record."""


class SpecialistAgentOrchestrator:
    """Runs the four required specialist agents with bounded concurrency."""

    def __init__(
        self,
        *,
        listing_service: ListingAgentService | None = None,
        public_records_service: PublicRecordsAgentService | None = None,
        comparable_service: ComparableAgentService | None = None,
        neighborhood_service: NeighborhoodAgentService | None = None,
        config: AgentRuntimeConfig | None = None,
    ) -> None:
        self._config = config or AgentRuntimeConfig.from_env()
        self._listing_service = listing_service or ListingAgentService(config=self._config)
        self._public_records_service = public_records_service or PublicRecordsAgentService(
            config=self._config
        )
        self._comparable_service = comparable_service or ComparableAgentService(config=self._config)
        self._neighborhood_service = neighborhood_service or NeighborhoodAgentService(
            config=self._config
        )

    async def run(self, context: AgentRunContext) -> SpecialistWorkflowResponse:
        started_perf = time.perf_counter()
        started_at = datetime.now(UTC)
        semaphore = asyncio.Semaphore(self._config.max_parallel_agents)

        logger.info(
            "Starting specialist workflow request_id=%s analysis_id=%s concurrency=%s",
            context.request_id,
            context.analysis_id,
            self._config.max_parallel_agents,
        )

        async def run_required(
            agent_name: AgentName,
            service: RunWithRecordService,
        ) -> tuple[AgentName, object | None, AgentRunRecord]:
            async with semaphore:
                return await self._execute_agent_with_retry(agent_name, service, context)

        task_specs: list[tuple[AgentName, RunWithRecordService]] = [
            (AgentName.LISTING, self._listing_service),
            (AgentName.PUBLIC_RECORDS, self._public_records_service),
            (AgentName.COMPARABLE, self._comparable_service),
            (AgentName.NEIGHBORHOOD, self._neighborhood_service),
        ]
        tasks = [
            asyncio.create_task(run_required(agent_name, service), name=str(agent_name))
            for agent_name, service in task_specs
        ]

        done, pending = await asyncio.wait(
            tasks,
            timeout=self._config.workflow_timeout_seconds,
        )
        workflow_timed_out = bool(pending)
        if workflow_timed_out:
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)

        completed_results = [task.result() for task in done if not task.cancelled()]
        result_lookup = {agent_name: output for agent_name, output, _ in completed_results}
        record_lookup = {agent_name: record for agent_name, _, record in completed_results}
        for agent_name, _service in task_specs:
            result_lookup.setdefault(agent_name, None)
            if agent_name not in record_lookup:
                record_lookup[agent_name] = self._build_workflow_timeout_record(
                    agent_name=agent_name,
                    context=context,
                    started_at=started_at,
                    started_perf=started_perf,
                )

        ordered_agent_names = [agent_name for agent_name, _service in task_specs]
        results = [
            (agent_name, result_lookup[agent_name], record_lookup[agent_name])
            for agent_name in ordered_agent_names
        ]

        run_records = [record for _, _, record in results]
        result_map = {agent_name: output for agent_name, output, _ in results}
        completed_agents = [
            record.agent_name for record in run_records if record.status == AgentRunStatus.COMPLETED
        ]
        failed_agents = [
            record.agent_name for record in run_records if record.status != AgentRunStatus.COMPLETED
        ]
        partial_failure = bool(completed_agents) and bool(failed_agents)

        if completed_agents and not failed_agents:
            workflow_status = WorkflowStatus.COMPLETED
        elif completed_agents:
            workflow_status = WorkflowStatus.PARTIAL
        else:
            workflow_status = WorkflowStatus.FAILED

        warnings = [
            f"{record.agent_name}:{record.error_code}"
            for record in run_records
            if record.error_code is not None
        ]
        if workflow_timed_out:
            warnings.append(f"workflow:{WorkflowTimeoutError.code}")
        usage = AgentUsageSummary()
        for record in run_records:
            usage.requests += record.usage.requests
            usage.input_tokens += record.usage.input_tokens
            usage.output_tokens += record.usage.output_tokens
            usage.total_tokens += record.usage.total_tokens

        metadata = SpecialistWorkflowMetadata(
            request_id=context.request_id,
            analysis_id=context.analysis_id,
            workflow_name=context.agent_config.tracing.workflow_name,
            workflow_status=workflow_status,
            started_at=started_at,
            completed_at=datetime.now(UTC),
            total_duration_ms=int((time.perf_counter() - started_perf) * 1000),
            completed_agents=completed_agents,
            failed_agents=failed_agents,
            partial_failure=partial_failure,
            usage=usage,
            run_records=run_records,
            trace_metadata={
                "request_id": context.request_id,
                "analysis_id": context.analysis_id or "",
                "prompt_version": context.agent_config.prompt_version,
                "workflow_timed_out": str(workflow_timed_out).lower(),
            },
            warnings=warnings,
        )
        logger.info(
            (
                "Finished specialist workflow request_id=%s status=%s "
                "completed=%s failed=%s duration_ms=%s"
            ),
            context.request_id,
            workflow_status,
            len(completed_agents),
            len(failed_agents),
            metadata.total_duration_ms,
        )
        return SpecialistWorkflowResponse(
            success=workflow_status != WorkflowStatus.FAILED,
            result=SpecialistWorkflowResult(
                listing_analysis=cast(
                    ListingAgentOutput | None,
                    result_map[AgentName.LISTING],
                ),
                public_records_analysis=cast(
                    PublicRecordsAgentOutput | None,
                    result_map[AgentName.PUBLIC_RECORDS],
                ),
                comparable_analysis=cast(
                    ComparableAgentOutput | None,
                    result_map[AgentName.COMPARABLE],
                ),
                neighborhood_analysis=cast(
                    NeighborhoodAgentOutput | None,
                    result_map[AgentName.NEIGHBORHOOD],
                ),
                metadata=metadata,
                warnings=warnings,
            ),
        )

    async def _execute_agent_with_retry(
        self,
        agent_name: AgentName,
        service: RunWithRecordService,
        context: AgentRunContext,
    ) -> tuple[AgentName, object | None, AgentRunRecord]:
        attempts = self._config.retry_attempts + 1
        last_record: AgentRunRecord | None = None
        for attempt in range(1, attempts + 1):
            started_at = datetime.now(UTC)
            started_perf = time.perf_counter()
            try:
                logger.info(
                    "Running specialist agent request_id=%s agent=%s attempt=%s",
                    context.request_id,
                    agent_name,
                    attempt,
                )
                run_result = await asyncio.wait_for(
                    service.run_with_record(context),
                    timeout=self._config.timeout_seconds,
                )
                record = run_result.record.model_copy(update={"attempt_count": attempt})
                return agent_name, run_result.output, record
            except TimeoutError:
                last_record = AgentRunRecord(
                    agent_name=agent_name,
                    status=AgentRunStatus.TIMED_OUT,
                    attempt_count=attempt,
                    started_at=started_at,
                    completed_at=datetime.now(UTC),
                    duration_ms=int((time.perf_counter() - started_perf) * 1000),
                    timed_out=True,
                    output_available=False,
                    error_code=AgentTimeoutError.code,
                    error_message=AgentTimeoutError.message,
                    retryable=attempt < attempts,
                    trace_metadata={
                        "request_id": context.request_id,
                        "analysis_id": context.analysis_id or "",
                    },
                )
            except AgentResearchError as exc:
                last_record = AgentRunRecord(
                    agent_name=agent_name,
                    status=AgentRunStatus.FAILED,
                    attempt_count=attempt,
                    started_at=started_at,
                    completed_at=datetime.now(UTC),
                    duration_ms=int((time.perf_counter() - started_perf) * 1000),
                    output_available=False,
                    error_code=exc.code,
                    error_message=exc.message,
                    retryable=exc.retryable and attempt < attempts,
                    trace_metadata={
                        "request_id": context.request_id,
                        "analysis_id": context.analysis_id or "",
                    },
                )
                if not exc.retryable:
                    break

        assert last_record is not None
        return agent_name, None, last_record

    def _build_workflow_timeout_record(
        self,
        *,
        agent_name: AgentName,
        context: AgentRunContext,
        started_at: datetime,
        started_perf: float,
    ) -> AgentRunRecord:
        return AgentRunRecord(
            agent_name=agent_name,
            status=AgentRunStatus.TIMED_OUT,
            started_at=started_at,
            completed_at=datetime.now(UTC),
            duration_ms=int((time.perf_counter() - started_perf) * 1000),
            timed_out=True,
            output_available=False,
            error_code=WorkflowTimeoutError.code,
            error_message=WorkflowTimeoutError.message,
            retryable=False,
            trace_metadata={
                "request_id": context.request_id,
                "analysis_id": context.analysis_id or "",
            },
        )
