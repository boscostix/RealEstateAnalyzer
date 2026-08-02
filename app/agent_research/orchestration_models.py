"""Models for deterministic parallel specialist-agent orchestration."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import Field, field_validator

from app.agent_research.models import AgentModel
from app.agent_research.specialist_models import (
    ComparableAgentOutput,
    ListingAgentOutput,
    NeighborhoodAgentOutput,
    PublicRecordsAgentOutput,
)
from app.agent_research.versioning import AgentName


class AgentRunStatus(StrEnum):
    """Final status for one specialist-agent run record."""

    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"


class WorkflowStatus(StrEnum):
    """Aggregate workflow status across required specialist agents."""

    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class AgentUsageSummary(AgentModel):
    """Usage totals captured for one agent or for a whole workflow."""

    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class AgentRunRecord(AgentModel):
    """Structured execution record for one specialist agent."""

    agent_name: AgentName
    status: AgentRunStatus
    attempt_count: int = 1
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    duration_ms: int = 0
    timed_out: bool = False
    output_available: bool = False
    usage: AgentUsageSummary = Field(default_factory=AgentUsageSummary)
    warnings: list[str] = Field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None
    retryable: bool = False
    trace_metadata: dict[str, str] = Field(default_factory=dict)

    @field_validator("duration_ms")
    @classmethod
    def validate_duration_ms(cls, value: int) -> int:
        if value < 0:
            raise ValueError("duration_ms must be non-negative.")
        return value


class SpecialistWorkflowMetadata(AgentModel):
    """Execution metadata for the first-four-agent workflow."""

    request_id: str
    analysis_id: str | None = None
    workflow_name: str
    workflow_status: WorkflowStatus
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    total_duration_ms: int = 0
    completed_agents: list[AgentName] = Field(default_factory=list)
    failed_agents: list[AgentName] = Field(default_factory=list)
    partial_failure: bool = False
    usage: AgentUsageSummary = Field(default_factory=AgentUsageSummary)
    run_records: list[AgentRunRecord] = Field(default_factory=list)
    trace_metadata: dict[str, str] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class SpecialistWorkflowResult(AgentModel):
    """Explicit partial workflow result for the first four specialist agents."""

    listing_analysis: ListingAgentOutput | None = None
    public_records_analysis: PublicRecordsAgentOutput | None = None
    comparable_analysis: ComparableAgentOutput | None = None
    neighborhood_analysis: NeighborhoodAgentOutput | None = None
    metadata: SpecialistWorkflowMetadata
    warnings: list[str] = Field(default_factory=list)


class SpecialistWorkflowResponse(AgentModel):
    """Response envelope for deterministic specialist-agent orchestration."""

    success: bool
    result: SpecialistWorkflowResult | None = None
