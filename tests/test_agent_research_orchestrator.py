"""Tests for deterministic parallel specialist-agent orchestration."""

from __future__ import annotations

import asyncio

import pytest

from app.agent_research import (
    AgentRunRecord,
    AgentRunStatus,
    AgentRuntimeConfig,
    AgentUsageSummary,
    SpecialistAgentOrchestrator,
    WorkflowStatus,
)
from app.agent_research.exceptions import AgentModelFailureError
from app.agent_research.services import ServiceRunResult
from app.agent_research.versioning import AgentName
from tests.agent_sdk_utils import (
    make_agent_context,
    make_comparable_agent_output,
    make_listing_agent_output,
    make_neighborhood_agent_output,
    make_public_records_agent_output,
)


class StaticAgentService:
    """Returns one successful service result immediately."""

    def __init__(self, agent_name: AgentName, output: object, *, usage_requests: int = 1) -> None:
        self.agent_name = agent_name
        self.output = output
        self.usage_requests = usage_requests
        self.calls = 0

    async def run_with_record(self, context: object) -> ServiceRunResult[object]:
        del context
        self.calls += 1
        return ServiceRunResult(
            output=self.output,
            record=AgentRunRecord(
                agent_name=self.agent_name,
                status=AgentRunStatus.COMPLETED,
                output_available=True,
                usage=AgentUsageSummary(
                    requests=self.usage_requests,
                    input_tokens=100 * self.usage_requests,
                    output_tokens=50 * self.usage_requests,
                    total_tokens=150 * self.usage_requests,
                ),
            ),
        )


class RetryThenSuccessService:
    """Fails once with a retryable error and then succeeds."""

    def __init__(self, agent_name: AgentName, output: object) -> None:
        self.agent_name = agent_name
        self.output = output
        self.calls = 0

    async def run_with_record(self, context: object) -> ServiceRunResult[object]:
        del context
        self.calls += 1
        if self.calls == 1:
            raise AgentModelFailureError(message="Transient model failure.")
        return ServiceRunResult(
            output=self.output,
            record=AgentRunRecord(
                agent_name=self.agent_name,
                status=AgentRunStatus.COMPLETED,
                output_available=True,
                usage=AgentUsageSummary(
                    requests=1,
                    input_tokens=100,
                    output_tokens=50,
                    total_tokens=150,
                ),
            ),
        )


class PermanentFailureService:
    """Always raises a non-retryable failure."""

    def __init__(self, error: AgentModelFailureError) -> None:
        self.error = error
        self.calls = 0

    async def run_with_record(self, context: object) -> ServiceRunResult[object]:
        del context
        self.calls += 1
        raise self.error


class ConcurrencyTrackingService:
    """Sleeps briefly while tracking the number of active executions."""

    def __init__(self, agent_name: AgentName, output: object, state: dict[str, int]) -> None:
        self.agent_name = agent_name
        self.output = output
        self.state = state

    async def run_with_record(self, context: object) -> ServiceRunResult[object]:
        del context
        self.state["active"] += 1
        self.state["max_seen"] = max(self.state["max_seen"], self.state["active"])
        try:
            await asyncio.sleep(0.03)
            return ServiceRunResult(
                output=self.output,
                record=AgentRunRecord(
                    agent_name=self.agent_name,
                    status=AgentRunStatus.COMPLETED,
                    output_available=True,
                    usage=AgentUsageSummary(requests=1, total_tokens=1),
                ),
            )
        finally:
            self.state["active"] -= 1


class SlowService:
    """Sleeps long enough to hit per-agent or workflow timeouts."""

    def __init__(self, agent_name: AgentName, output: object, *, delay_seconds: float) -> None:
        self.agent_name = agent_name
        self.output = output
        self.delay_seconds = delay_seconds
        self.calls = 0

    async def run_with_record(self, context: object) -> ServiceRunResult[object]:
        del context
        self.calls += 1
        await asyncio.sleep(self.delay_seconds)
        return ServiceRunResult(
            output=self.output,
            record=AgentRunRecord(
                agent_name=self.agent_name,
                status=AgentRunStatus.COMPLETED,
                output_available=True,
                usage=AgentUsageSummary(requests=1, total_tokens=1),
            ),
        )


def build_orchestrator(
    *,
    listing_service: object | None = None,
    public_records_service: object | None = None,
    comparable_service: object | None = None,
    neighborhood_service: object | None = None,
    config: AgentRuntimeConfig | None = None,
) -> SpecialistAgentOrchestrator:
    return SpecialistAgentOrchestrator(
        listing_service=listing_service
        or StaticAgentService(AgentName.LISTING, make_listing_agent_output()),
        public_records_service=public_records_service
        or StaticAgentService(AgentName.PUBLIC_RECORDS, make_public_records_agent_output()),
        comparable_service=comparable_service
        or StaticAgentService(AgentName.COMPARABLE, make_comparable_agent_output()),
        neighborhood_service=neighborhood_service
        or StaticAgentService(AgentName.NEIGHBORHOOD, make_neighborhood_agent_output()),
        config=config or AgentRuntimeConfig(),
    )


@pytest.mark.asyncio
async def test_specialist_agent_orchestrator_runs_required_agents_in_parallel() -> None:
    state = {"active": 0, "max_seen": 0}
    orchestrator = build_orchestrator(
        listing_service=ConcurrencyTrackingService(
            AgentName.LISTING, make_listing_agent_output(), state
        ),
        public_records_service=ConcurrencyTrackingService(
            AgentName.PUBLIC_RECORDS, make_public_records_agent_output(), state
        ),
        comparable_service=ConcurrencyTrackingService(
            AgentName.COMPARABLE, make_comparable_agent_output(), state
        ),
        neighborhood_service=ConcurrencyTrackingService(
            AgentName.NEIGHBORHOOD, make_neighborhood_agent_output(), state
        ),
        config=AgentRuntimeConfig(
            max_parallel_agents=2, timeout_seconds=1, workflow_timeout_seconds=1
        ),
    )

    response = await orchestrator.run(make_agent_context())

    assert response.success is True
    assert response.result is not None
    assert response.result.metadata.workflow_status == WorkflowStatus.COMPLETED
    assert state["max_seen"] == 2
    assert response.result.metadata.completed_agents == [
        AgentName.LISTING,
        AgentName.PUBLIC_RECORDS,
        AgentName.COMPARABLE,
        AgentName.NEIGHBORHOOD,
    ]


@pytest.mark.asyncio
async def test_specialist_agent_orchestrator_retries_retryable_agent_failures() -> None:
    retry_service = RetryThenSuccessService(AgentName.COMPARABLE, make_comparable_agent_output())
    orchestrator = build_orchestrator(
        comparable_service=retry_service,
        config=AgentRuntimeConfig(retry_attempts=1, timeout_seconds=1, workflow_timeout_seconds=1),
    )

    response = await orchestrator.run(make_agent_context())

    assert response.success is True
    assert response.result is not None
    assert retry_service.calls == 2
    comparable_record = next(
        record
        for record in response.result.metadata.run_records
        if record.agent_name == AgentName.COMPARABLE
    )
    assert comparable_record.status == AgentRunStatus.COMPLETED
    assert comparable_record.attempt_count == 2


@pytest.mark.asyncio
async def test_specialist_agent_orchestrator_returns_partial_results_on_agent_failure() -> None:
    error = AgentModelFailureError(message="Fatal model failure.")
    error.retryable = False
    orchestrator = build_orchestrator(
        neighborhood_service=PermanentFailureService(error),
        config=AgentRuntimeConfig(retry_attempts=2, timeout_seconds=1, workflow_timeout_seconds=1),
    )

    response = await orchestrator.run(make_agent_context())

    assert response.success is True
    assert response.result is not None
    assert response.result.neighborhood_analysis is None
    assert response.result.metadata.workflow_status == WorkflowStatus.PARTIAL
    assert response.result.metadata.failed_agents == [AgentName.NEIGHBORHOOD]
    failed_record = next(
        record
        for record in response.result.metadata.run_records
        if record.agent_name == AgentName.NEIGHBORHOOD
    )
    assert failed_record.status == AgentRunStatus.FAILED
    assert failed_record.error_code == AgentModelFailureError.code


@pytest.mark.asyncio
async def test_specialist_agent_orchestrator_marks_agent_timeouts_explicitly() -> None:
    orchestrator = build_orchestrator(
        public_records_service=SlowService(
            AgentName.PUBLIC_RECORDS,
            make_public_records_agent_output(),
            delay_seconds=0.05,
        ),
        config=AgentRuntimeConfig(
            retry_attempts=0,
            timeout_seconds=0.01,
            workflow_timeout_seconds=1,
        ),
    )

    response = await orchestrator.run(make_agent_context())

    assert response.success is True
    assert response.result is not None
    assert response.result.public_records_analysis is None
    timeout_record = next(
        record
        for record in response.result.metadata.run_records
        if record.agent_name == AgentName.PUBLIC_RECORDS
    )
    assert timeout_record.status == AgentRunStatus.TIMED_OUT
    assert timeout_record.error_code == "agent_timeout"
    assert timeout_record.timed_out is True


@pytest.mark.asyncio
async def test_specialist_agent_orchestrator_marks_workflow_timeout_and_preserves_partials() -> (
    None
):
    orchestrator = build_orchestrator(
        listing_service=StaticAgentService(AgentName.LISTING, make_listing_agent_output()),
        public_records_service=SlowService(
            AgentName.PUBLIC_RECORDS,
            make_public_records_agent_output(),
            delay_seconds=0.05,
        ),
        comparable_service=SlowService(
            AgentName.COMPARABLE,
            make_comparable_agent_output(),
            delay_seconds=0.05,
        ),
        neighborhood_service=SlowService(
            AgentName.NEIGHBORHOOD,
            make_neighborhood_agent_output(),
            delay_seconds=0.05,
        ),
        config=AgentRuntimeConfig(
            retry_attempts=0,
            timeout_seconds=1,
            workflow_timeout_seconds=0.01,
            max_parallel_agents=4,
        ),
    )

    response = await orchestrator.run(make_agent_context())

    assert response.success is True
    assert response.result is not None
    assert response.result.listing_analysis is not None
    assert response.result.metadata.workflow_status == WorkflowStatus.PARTIAL
    assert "workflow:workflow_timeout" in response.result.metadata.warnings
    timed_out_records = [
        record for record in response.result.metadata.run_records if record.timed_out
    ]
    assert len(timed_out_records) == 3
    assert all(record.error_code == "workflow_timeout" for record in timed_out_records)


@pytest.mark.asyncio
async def test_specialist_agent_orchestrator_aggregates_usage_metadata() -> None:
    orchestrator = build_orchestrator(
        listing_service=StaticAgentService(
            AgentName.LISTING,
            make_listing_agent_output(),
            usage_requests=2,
        ),
        public_records_service=StaticAgentService(
            AgentName.PUBLIC_RECORDS,
            make_public_records_agent_output(),
            usage_requests=3,
        ),
        comparable_service=StaticAgentService(
            AgentName.COMPARABLE,
            make_comparable_agent_output(),
            usage_requests=4,
        ),
        neighborhood_service=StaticAgentService(
            AgentName.NEIGHBORHOOD,
            make_neighborhood_agent_output(),
            usage_requests=5,
        ),
    )

    response = await orchestrator.run(make_agent_context())

    assert response.result is not None
    assert response.result.metadata.usage.requests == 14
    assert response.result.metadata.usage.input_tokens == 1400
    assert response.result.metadata.usage.output_tokens == 700
    assert response.result.metadata.usage.total_tokens == 2100
