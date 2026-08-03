"""Stable, versioned model-input contracts for the investment committee."""

from __future__ import annotations

from decimal import Decimal

from pydantic import Field

from app.agent_research.models import (
    ConflictMateriality,
    ConflictResolutionStatus,
    EvidenceReference,
    FindingSeverity,
)
from app.investment_committee.models import (
    CommitteeMissingItem,
    CommitteeModel,
    RecommendationPolicyDecision,
)
from app.investment_committee.versioning import COMMITTEE_INPUT_FORMAT_VERSION


class CommitteePreparedField(CommitteeModel):
    field_name: str
    final_value: str | int | Decimal | None = None
    extracted_value: str | int | Decimal | None = None
    status: str
    source: str | None = None
    confidence: Decimal | None = None
    source_path: str
    evidence: list[EvidenceReference] = Field(default_factory=list)


class CommitteePreparedAssumption(CommitteeModel):
    name: str
    value: str | int | Decimal | None
    source_path: str
    evidence: list[EvidenceReference] = Field(default_factory=list)


class CommitteePreparedMetric(CommitteeModel):
    metric_name: str
    value: str | int | Decimal | bool | None
    source_path: str
    description: str
    evidence: list[EvidenceReference] = Field(default_factory=list)


class CommitteePreparedFinding(CommitteeModel):
    finding_id: str
    source_agent: str
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


class CommitteePreparedConflictValue(CommitteeModel):
    value: str | int | Decimal | bool | None
    source_id: str
    source_type: str
    confidence: Decimal
    label: str | None = None
    field_path: str | None = None
    agent_name: str | None = None
    authoritative: bool = False
    verified: bool = False


class CommitteePreparedConflict(CommitteeModel):
    conflict_id: str
    field_or_topic: str
    materiality: ConflictMateriality
    resolution_status: ConflictResolutionStatus
    preferred_value: str | int | Decimal | bool | None = None
    preferred_source_id: str | None = None
    resolution_reason: str | None = None
    requires_user_review: bool
    requires_synthesis: bool = False
    values: list[CommitteePreparedConflictValue] = Field(default_factory=list)


class CommitteePreparedScenario(CommitteeModel):
    name: str
    source_path: str
    metrics: list[CommitteePreparedMetric] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CommitteePreparedStressTest(CommitteeModel):
    identifier: str
    description: str
    source_path: str
    changed_assumptions: list[CommitteePreparedAssumption] = Field(default_factory=list)
    metrics: list[CommitteePreparedMetric] = Field(default_factory=list)
    cash_flow_remains_positive: bool
    additional_cash_required: Decimal
    warnings: list[str] = Field(default_factory=list)


class CommitteePreparedAgentSummary(CommitteeModel):
    agent_name: str
    summary: str
    overall_confidence: Decimal
    findings_count: int
    missing_information: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CommitteePreparedResearch(CommitteeModel):
    overall_data_confidence: Decimal
    due_diligence_questions: list[str] = Field(default_factory=list)
    missing_information: list[CommitteeMissingItem] = Field(default_factory=list)
    consolidated_findings: list[CommitteePreparedFinding] = Field(default_factory=list)
    conflicts: list[CommitteePreparedConflict] = Field(default_factory=list)
    agent_summaries: list[CommitteePreparedAgentSummary] = Field(default_factory=list)
    evidence_index: list[EvidenceReference] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    partial_failure: bool = False


class CommitteeModelInput(CommitteeModel):
    format_version: str = COMMITTEE_INPUT_FORMAT_VERSION
    property_key: str
    property_fields: list[CommitteePreparedField] = Field(default_factory=list)
    assumptions: list[CommitteePreparedAssumption] = Field(default_factory=list)
    underwriting_metrics: list[CommitteePreparedMetric] = Field(default_factory=list)
    maximum_offer: list[CommitteePreparedMetric] = Field(default_factory=list)
    scenarios: list[CommitteePreparedScenario] = Field(default_factory=list)
    stress_tests: list[CommitteePreparedStressTest] = Field(default_factory=list)
    research: CommitteePreparedResearch
    policy: RecommendationPolicyDecision
    warnings: list[str] = Field(default_factory=list)
