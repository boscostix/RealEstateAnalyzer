"""Strict structured contracts for specialist agent outputs."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AgentModel(BaseModel):
    """Base model for strict agent-related schema objects."""

    model_config = ConfigDict(extra="forbid")


class EvidenceSourceType(StrEnum):
    """Supported evidence ownership categories."""

    RESEARCH_SOURCE = "research_source"
    RESEARCH_CITATION = "research_citation"
    VERIFIED_PROPERTY = "verified_property"
    UNDERWRITING = "underwriting"
    FUNCTION_TOOL = "function_tool"


def _validate_confidence_decimal(value: Decimal, *, field_name: str) -> Decimal:
    if value < 0 or value > 1:
        raise ValueError(f"{field_name} must be between 0 and 1.")
    return value


class FindingSeverity(StrEnum):
    """Relative severity for a specialist finding."""

    INFORMATIONAL = "informational"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ConflictMateriality(StrEnum):
    """Materiality for conflicting factual claims."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ConflictResolutionStatus(StrEnum):
    """Deterministic or human-resolution state for a preserved conflict."""

    RESOLVED_DETERMINISTICALLY = "resolved_deterministically"
    RESOLVED_BY_SYNTHESIS = "resolved_by_synthesis"
    UNRESOLVED = "unresolved"
    USER_REVIEW_REQUIRED = "user_review_required"


class EvidenceReference(AgentModel):
    """A normalized reference to deterministic evidence available to agents."""

    source_id: str
    source_type: EvidenceSourceType
    citation_id: str | None = None
    field_path: str | None = None
    supporting_excerpt: str | None = None
    retrieved_at: datetime | None = None

    @model_validator(mode="after")
    def validate_locator(self) -> EvidenceReference:
        if self.citation_id is None and self.field_path is None:
            raise ValueError("Evidence references must include a citation_id or field_path.")
        return self


class AgentFinding(AgentModel):
    """A typed finding emitted by a specialist agent."""

    finding_id: str
    category: str
    title: str
    finding: str
    significance: str
    severity: FindingSeverity
    confidence: Decimal
    evidence: list[EvidenceReference] = Field(default_factory=list)
    affected_fields: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    recommended_next_actions: list[str] = Field(default_factory=list)
    is_inference: bool

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: Decimal) -> Decimal:
        return _validate_confidence_decimal(value, field_name="confidence")

    @model_validator(mode="after")
    def validate_evidence(self) -> AgentFinding:
        if not self.evidence:
            raise ValueError("Agent findings must include at least one evidence reference.")
        return self


class AgentConflictCandidate(AgentModel):
    """A potential conflict surfaced by one specialist agent."""

    field_or_topic: str
    values_or_claims: list[str] = Field(min_length=2)
    source_ids: list[str] = Field(min_length=2)
    description: str
    materiality: ConflictMateriality


class ConflictValue(AgentModel):
    """One competing value preserved inside a normalized conflict."""

    value: Any
    source_id: str
    source_type: str
    confidence: Decimal
    label: str | None = None
    field_path: str | None = None
    agent_name: str | None = None
    authoritative: bool = False
    verified: bool = False
    retrieved_at: datetime | None = None

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: Decimal) -> Decimal:
        return _validate_confidence_decimal(value, field_name="confidence")


class ResearchConflict(AgentModel):
    """A normalized cross-source conflict preserved for later review."""

    conflict_id: str
    field_or_topic: str
    values: list[ConflictValue] = Field(min_length=2)
    materiality: ConflictMateriality
    resolution_status: ConflictResolutionStatus
    preferred_value: Any | None = None
    preferred_source_id: str | None = None
    resolution_reason: str | None = None
    requires_user_review: bool
    source_precedence_applied: bool = False
    requires_synthesis: bool = False


class DuplicateFindingGroup(AgentModel):
    """A deterministic duplicate-finding cluster across specialist agents."""

    duplicate_id: str
    canonical_finding_id: str
    duplicate_finding_ids: list[str] = Field(default_factory=list)
    agent_names: list[str] = Field(default_factory=list)
    shared_signature: str
    requires_user_review: bool = False


class CrossDomainRelationship(AgentModel):
    """A grouped cross-domain signal spanning more than one specialist agent."""

    relationship_id: str
    topic: str
    summary: str
    finding_ids: list[str] = Field(default_factory=list)
    agent_names: list[str] = Field(default_factory=list)
    affected_fields: list[str] = Field(default_factory=list)
    evidence: list[EvidenceReference] = Field(default_factory=list)


class AgentExecutionMetadata(AgentModel):
    """Execution metadata shared by specialist and synthesized outputs."""

    request_id: str
    workflow_name: str
    workflow_version: str
    prompt_version: str
    model_name: str
    agent_versions: dict[str, str] = Field(default_factory=dict)
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    total_duration_ms: int = 0
    agent_latencies_ms: dict[str, int] = Field(default_factory=dict)
    traced: bool = False
    usage_requests: int = 0
    usage_input_tokens: int = 0
    usage_output_tokens: int = 0
    usage_total_tokens: int = 0
    trace_metadata: dict[str, str] = Field(default_factory=dict)
    partial_failure: bool = False
    warnings: list[str] = Field(default_factory=list)

    @field_validator("total_duration_ms")
    @classmethod
    def validate_total_duration_ms(cls, value: int) -> int:
        if value < 0:
            raise ValueError("total_duration_ms must be non-negative.")
        return value

    @field_validator(
        "usage_requests",
        "usage_input_tokens",
        "usage_output_tokens",
        "usage_total_tokens",
    )
    @classmethod
    def validate_usage_counts(cls, value: int) -> int:
        if value < 0:
            raise ValueError("usage counts must be non-negative.")
        return value

    @field_validator("agent_latencies_ms")
    @classmethod
    def validate_agent_latencies_ms(cls, value: dict[str, int]) -> dict[str, int]:
        for latency in value.values():
            if latency < 0:
                raise ValueError("agent_latencies_ms values must be non-negative.")
        return value

    @model_validator(mode="after")
    def validate_completed_at(self) -> AgentExecutionMetadata:
        if self.completed_at < self.started_at:
            raise ValueError("completed_at must be greater than or equal to started_at.")
        return self


class AgentResearchOutput(AgentModel):
    """The strict structured output contract for every specialist agent."""

    agent_name: str
    agent_version: str
    prompt_version: str
    summary: str
    overall_confidence: Decimal
    findings: list[AgentFinding] = Field(default_factory=list)
    conflicts: list[AgentConflictCandidate] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    due_diligence_questions: list[str] = Field(default_factory=list)
    sources_used: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @field_validator("overall_confidence")
    @classmethod
    def validate_overall_confidence(cls, value: Decimal) -> Decimal:
        return _validate_confidence_decimal(value, field_name="overall_confidence")


class UnifiedAgentResearchPackage(AgentModel):
    """Validated synthesized package assembled from all specialist outputs."""

    listing_analysis: AgentResearchOutput | None = None
    public_records_analysis: AgentResearchOutput | None = None
    comparable_analysis: AgentResearchOutput | None = None
    neighborhood_analysis: AgentResearchOutput | None = None
    risk_analysis: AgentResearchOutput | None = None
    consolidated_findings: list[AgentFinding] = Field(default_factory=list)
    cross_domain_relationships: list[CrossDomainRelationship] = Field(default_factory=list)
    conflicts: list[ResearchConflict] = Field(default_factory=list)
    duplicate_findings: list[DuplicateFindingGroup] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    due_diligence_questions: list[str] = Field(default_factory=list)
    evidence_index: list[EvidenceReference] = Field(default_factory=list)
    overall_data_confidence: Decimal
    warnings: list[str] = Field(default_factory=list)
    execution_metadata: AgentExecutionMetadata

    @field_validator("overall_data_confidence")
    @classmethod
    def validate_overall_data_confidence(cls, value: Decimal) -> Decimal:
        return _validate_confidence_decimal(value, field_name="overall_data_confidence")
