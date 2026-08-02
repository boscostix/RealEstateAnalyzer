"""Risk-agent-specific input and output models."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import Field, field_validator

from app.agent_research.models import (
    AgentModel,
    AgentResearchOutput,
    DuplicateFindingGroup,
    EvidenceReference,
    FindingSeverity,
    ResearchConflict,
)
from app.agent_research.specialist_models import (
    ComparableAgentOutput,
    ListingAgentOutput,
    NeighborhoodAgentOutput,
    PublicRecordsAgentOutput,
)
from app.agent_research.tool_models import UnderwritingSummaryPayload
from app.models.verification import VerifiedPropertySnapshot


class RiskCategory(StrEnum):
    """Normalized risk buckets for the Property Risk Agent."""

    PHYSICAL_CONDITION = "physical_condition"
    FINANCIAL_FRAGILITY = "financial_fragility"
    ENVIRONMENTAL_EXPOSURE = "environmental_exposure"
    REGULATORY_COMPLIANCE = "regulatory_compliance"
    MARKET_LIQUIDITY = "market_liquidity"
    DATA_GAP = "data_gap"


class InspectionPriority(StrEnum):
    """Priority band for follow-up inspection work."""

    IMMEDIATE = "immediate"
    HIGH = "high"
    ROUTINE = "routine"
    MONITOR = "monitor"


class SellerQuestionPriority(StrEnum):
    """Priority band for seller-directed follow-up questions."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RiskStressTestSummary(AgentModel):
    """Sanitized stress-test slice relevant to financial fragility."""

    identifier: str
    description: str
    change_in_monthly_cash_flow: Decimal
    additional_cash_required: Decimal
    cash_flow_remains_positive: bool
    stressed_dscr: Decimal | None = None
    warnings: list[str] = Field(default_factory=list)


class RiskFinding(AgentModel):
    """One structured risk emitted by the Property Risk Agent."""

    risk_id: str
    category: RiskCategory
    title: str
    summary: str
    significance: str
    severity: FindingSeverity
    confidence: Decimal
    evidence: list[EvidenceReference] = Field(default_factory=list)
    affected_fields: list[str] = Field(default_factory=list)
    inspection_priority: InspectionPriority | None = None
    seller_question_ids: list[str] = Field(default_factory=list)
    recommended_next_actions: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    is_missing_data_risk: bool = False
    requires_specialist_review: bool = False

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, value: Decimal) -> Decimal:
        if value < 0 or value > 1:
            raise ValueError("confidence must be between 0 and 1.")
        return value


class InspectionPriorityItem(AgentModel):
    """Inspection follow-up requested by the Property Risk Agent."""

    item_id: str
    title: str
    priority: InspectionPriority
    rationale: str
    related_risk_ids: list[str] = Field(default_factory=list)
    evidence: list[EvidenceReference] = Field(default_factory=list)


class SellerQuestion(AgentModel):
    """Seller-facing follow-up question with deterministic rationale."""

    question_id: str
    question: str
    priority: SellerQuestionPriority
    rationale: str
    related_risk_ids: list[str] = Field(default_factory=list)
    evidence: list[EvidenceReference] = Field(default_factory=list)


class PropertyRiskAgentInput(AgentModel):
    """Validated upstream context passed to the Property Risk Agent."""

    property_key: str
    request_id: str
    analysis_id: str | None = None
    verified_property: VerifiedPropertySnapshot
    listing_analysis: ListingAgentOutput
    public_records_analysis: PublicRecordsAgentOutput
    comparable_analysis: ComparableAgentOutput
    neighborhood_analysis: NeighborhoodAgentOutput
    conflicts: list[ResearchConflict] = Field(default_factory=list)
    duplicate_findings: list[DuplicateFindingGroup] = Field(default_factory=list)
    upstream_data_confidence: Decimal
    underwriting_summary: UnderwritingSummaryPayload | None = None
    stress_tests: list[RiskStressTestSummary] = Field(default_factory=list)
    upstream_warnings: list[str] = Field(default_factory=list)

    @field_validator("upstream_data_confidence")
    @classmethod
    def validate_upstream_data_confidence(cls, value: Decimal) -> Decimal:
        if value < 0 or value > 1:
            raise ValueError("upstream_data_confidence must be between 0 and 1.")
        return value


class RiskGuardrailReport(AgentModel):
    """Risk-specific validation report returned by the guardrail layer."""

    unqualified_physical_risk_ids: list[str] = Field(default_factory=list)
    unsupported_financial_risk_ids: list[str] = Field(default_factory=list)
    diagnostic_claim_ids: list[str] = Field(default_factory=list)


class PropertyRiskAgentOutput(AgentResearchOutput):
    """Strict structured output for the Property Risk Agent."""

    agent_name: Literal["property_risk_agent"]
    risk_findings: list[RiskFinding] = Field(default_factory=list)
    inspection_priorities: list[InspectionPriorityItem] = Field(default_factory=list)
    seller_questions: list[SellerQuestion] = Field(default_factory=list)
