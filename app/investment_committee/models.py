"""Strict models for deterministic investment-committee reasoning."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.agent_research.models import (
    EvidenceReference,
    FindingSeverity,
    UnifiedAgentResearchPackage,
)
from app.investment_committee.versioning import (
    COMMITTEE_INPUT_FORMAT_VERSION,
    COMMITTEE_PROMPT_VERSION,
    CONFIDENCE_POLICY_VERSION,
    OFFER_RANGE_POLICY_VERSION,
    RECOMMENDATION_POLICY_VERSION,
)
from app.models.assumptions import AnalysisAssumptions
from app.models.underwriting import UnderwritingAnalysis
from app.models.verification import VerifiedPropertySnapshot


class CommitteeModel(BaseModel):
    """Base model for committee schema objects with strict field handling."""

    model_config = ConfigDict(extra="forbid")


def _validate_confidence_decimal(value: Decimal, *, field_name: str) -> Decimal:
    if value < 0 or value > 1:
        raise ValueError(f"{field_name} must be between 0 and 1.")
    return value


class InvestmentRecommendation(StrEnum):
    """Supported final recommendation labels for committee output."""

    STRONG_BUY = "strong_buy"
    BUY = "buy"
    BUY_ONLY_BELOW = "buy_only_below"
    NEGOTIATE = "negotiate"
    WATCH = "watch"
    PASS = "pass"
    INSUFFICIENT_INFORMATION = "insufficient_information"


RECOMMENDATION_LABEL_MEANINGS: dict[InvestmentRecommendation, str] = {
    InvestmentRecommendation.STRONG_BUY: (
        "Rare recommendation reserved for highly supported deals with strong resilience."
    ),
    InvestmentRecommendation.BUY: "Proceeding is reasonable under the current supported case.",
    InvestmentRecommendation.BUY_ONLY_BELOW: (
        "The property only works below an existing deterministic threshold."
    ),
    InvestmentRecommendation.NEGOTIATE: (
        "The deal may work with better pricing or terms, but not as-is."
    ),
    InvestmentRecommendation.WATCH: (
        "The property is not attractive enough now, but may improve with changes."
    ),
    InvestmentRecommendation.PASS: (
        "The investment thesis is materially unsupported even with further pursuit."
    ),
    InvestmentRecommendation.INSUFFICIENT_INFORMATION: (
        "Decision-critical gaps prevent a responsible recommendation."
    ),
}


class RiskTolerance(StrEnum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class ReasonImportance(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    DECISIVE = "decisive"


class AssumptionStatus(StrEnum):
    WELL_SUPPORTED = "well_supported"
    REASONABLE = "reasonable"
    OPTIMISTIC = "optimistic"
    WEAKLY_SUPPORTED = "weakly_supported"
    UNVERIFIED = "unverified"
    CONFLICTING = "conflicting"


class RiskProbability(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class DueDiligencePriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DueDiligenceTiming(StrEnum):
    BEFORE_OFFER = "before_offer"
    DURING_OPTION_PERIOD = "during_option_period"
    BEFORE_FINANCING = "before_financing"
    BEFORE_CLOSING = "before_closing"
    AFTER_PURCHASE = "after_purchase"


class MissingInformationMateriality(StrEnum):
    NON_MATERIAL = "non_material"
    IMPORTANT = "important"
    DECISION_CRITICAL = "decision_critical"


class DecisionContext(CommitteeModel):
    strategy: str = "long_term_rental"
    risk_tolerance: RiskTolerance = RiskTolerance.MODERATE
    desired_monthly_cash_flow: Decimal | None = None
    target_cap_rate_percent: Decimal | None = None
    target_cash_on_cash_return_percent: Decimal | None = None
    target_dscr: Decimal | None = None
    maximum_available_cash: Decimal | None = None
    desired_holding_period_years: int | None = None
    must_have_conditions: list[str] = Field(default_factory=list)
    deal_breakers: list[str] = Field(default_factory=list)


class InvestmentCommitteeInput(CommitteeModel):
    property: VerifiedPropertySnapshot
    assumptions: AnalysisAssumptions
    underwriting: UnderwritingAnalysis
    agent_research: UnifiedAgentResearchPackage
    decision_context: DecisionContext | None = None

    @model_validator(mode="after")
    def validate_consistency(self) -> InvestmentCommitteeInput:
        if self.property.source_url != self.underwriting.property.source_url:
            raise ValueError("property and underwriting.property must reference the same source.")
        if self.property.provider != self.underwriting.property.provider:
            raise ValueError("property and underwriting.property must reference the same provider.")
        if self.assumptions.purchase_price != self.underwriting.acquisition.purchase_price:
            raise ValueError("assumptions.purchase_price must match underwriting purchase price.")
        return self


class OfferRangeBasis(CommitteeModel):
    value: Decimal
    source_metric: str
    source_path: str
    description: str


class CommitteeReason(CommitteeModel):
    title: str
    explanation: str
    importance: ReasonImportance
    evidence: list[EvidenceReference] = Field(default_factory=list)
    affected_metrics: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_evidence(self) -> CommitteeReason:
        if not self.evidence:
            raise ValueError("Committee reasons must include at least one evidence reference.")
        return self


class KeyAssumptionAssessment(CommitteeModel):
    assumption_name: str
    value_used: str
    status: AssumptionStatus
    sensitivity: str
    evidence: list[EvidenceReference] = Field(default_factory=list)
    validation_needed: str | None = None

    @model_validator(mode="after")
    def validate_evidence(self) -> KeyAssumptionAssessment:
        if not self.evidence:
            raise ValueError(
                "Key assumption assessments must include at least one evidence reference."
            )
        return self


class CommitteeRisk(CommitteeModel):
    category: str
    title: str
    explanation: str
    severity: FindingSeverity
    probability: RiskProbability | None = None
    financial_impact: str | None = None
    evidence: list[EvidenceReference] = Field(default_factory=list)
    mitigation: str | None = None
    blocks_investment: bool

    @model_validator(mode="after")
    def validate_evidence(self) -> CommitteeRisk:
        if not self.evidence:
            raise ValueError("Committee risks must include at least one evidence reference.")
        return self


class CommitteeMissingItem(CommitteeModel):
    item: str
    materiality: MissingInformationMateriality
    importance: ReasonImportance
    reason_needed: str
    decision_impact: str
    recommended_source: str | None = None
    blocks_recommendation: bool


class RequiredCondition(CommitteeModel):
    condition: str
    current_status: str
    threshold_or_requirement: str
    evidence: list[EvidenceReference] = Field(default_factory=list)
    consequence_if_false: str

    @model_validator(mode="after")
    def validate_evidence(self) -> RequiredCondition:
        if not self.evidence:
            raise ValueError("Required conditions must include at least one evidence reference.")
        return self


class DueDiligenceItem(CommitteeModel):
    category: str
    action: str
    reason: str
    priority: DueDiligencePriority
    timing: DueDiligenceTiming
    responsible_party: str | None = None
    evidence: list[EvidenceReference] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_evidence(self) -> DueDiligenceItem:
        if not self.evidence:
            raise ValueError("Due-diligence items must include at least one evidence reference.")
        return self


class NegotiationPoint(CommitteeModel):
    issue: str
    negotiation_request: str
    rationale: str
    evidence: list[EvidenceReference] = Field(default_factory=list)
    estimated_value: Decimal | None = None

    @model_validator(mode="after")
    def validate_evidence(self) -> NegotiationPoint:
        if not self.evidence:
            raise ValueError("Negotiation points must include at least one evidence reference.")
        return self


class InvestmentCommitteeOutput(CommitteeModel):
    recommendation: InvestmentRecommendation
    recommendation_summary: str
    recommendation_confidence: Decimal
    recommendation_confidence_reasons: list[str] = Field(default_factory=list)
    asking_price: Decimal
    supported_offer_low: Decimal | None = None
    supported_offer_high: Decimal | None = None
    recommended_offer_basis: list[OfferRangeBasis] = Field(default_factory=list)
    investment_thesis: str
    strongest_upside: str
    strongest_downside: str
    reasons_to_proceed: list[CommitteeReason] = Field(default_factory=list)
    reasons_not_to_proceed: list[CommitteeReason] = Field(default_factory=list)
    key_assumptions: list[KeyAssumptionAssessment] = Field(default_factory=list)
    fragile_assumptions: list[KeyAssumptionAssessment] = Field(default_factory=list)
    material_risks: list[CommitteeRisk] = Field(default_factory=list)
    missing_information: list[CommitteeMissingItem] = Field(default_factory=list)
    unresolved_conflicts: list[str] = Field(default_factory=list)
    what_must_be_true: list[RequiredCondition] = Field(default_factory=list)
    due_diligence_checklist: list[DueDiligenceItem] = Field(default_factory=list)
    negotiation_points: list[NegotiationPoint] = Field(default_factory=list)
    conditions_before_offer: list[str] = Field(default_factory=list)
    conditions_before_closing: list[str] = Field(default_factory=list)
    evidence_references: list[EvidenceReference] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @field_validator("recommendation_confidence")
    @classmethod
    def validate_recommendation_confidence(cls, value: Decimal) -> Decimal:
        return _validate_confidence_decimal(value, field_name="recommendation_confidence")

    @model_validator(mode="after")
    def validate_offer_consistency(self) -> InvestmentCommitteeOutput:
        if self.supported_offer_low is not None and self.supported_offer_high is None:
            raise ValueError("supported_offer_high is required when supported_offer_low is set.")
        if self.supported_offer_low is None and self.supported_offer_high is not None:
            raise ValueError("supported_offer_low is required when supported_offer_high is set.")
        if (
            self.supported_offer_low is not None
            and self.supported_offer_high is not None
            and self.supported_offer_low > self.supported_offer_high
        ):
            raise ValueError(
                "supported_offer_low must be less than or equal to supported_offer_high."
            )
        if (
            self.recommendation == InvestmentRecommendation.BUY_ONLY_BELOW
            and self.supported_offer_high is None
        ):
            raise ValueError("buy_only_below requires a supported offer threshold.")
        if (
            self.supported_offer_low is not None or self.supported_offer_high is not None
        ) and not self.recommended_offer_basis:
            raise ValueError("Offer-supported recommendations must include basis values.")
        return self


class CommitteePolicyVersions(CommitteeModel):
    prompt_version: str = COMMITTEE_PROMPT_VERSION
    input_format_version: str = COMMITTEE_INPUT_FORMAT_VERSION
    recommendation_policy_version: str = RECOMMENDATION_POLICY_VERSION
    offer_range_policy_version: str = OFFER_RANGE_POLICY_VERSION
    confidence_policy_version: str = CONFIDENCE_POLICY_VERSION


class DeterministicOfferRange(CommitteeModel):
    supported_offer_low: Decimal | None = None
    supported_offer_high: Decimal | None = None
    basis: list[OfferRangeBasis] = Field(default_factory=list)
    allowed_values: list[Decimal] = Field(default_factory=list)
    valid_threshold_exists: bool = False
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_range(self) -> DeterministicOfferRange:
        if self.supported_offer_low is None and self.supported_offer_high is None:
            if self.basis:
                raise ValueError("Offer basis cannot exist without a supported offer range.")
            return self
        if self.supported_offer_low is None or self.supported_offer_high is None:
            raise ValueError("Both supported offer boundaries must be set together.")
        if self.supported_offer_low > self.supported_offer_high:
            raise ValueError(
                "supported_offer_low must be less than or equal to supported_offer_high."
            )
        if not self.allowed_values:
            raise ValueError("Offer range must preserve deterministic allowed values.")
        return self


class ConfidencePolicyResult(CommitteeModel):
    maximum_confidence: Decimal
    reasons: list[str] = Field(default_factory=list)

    @field_validator("maximum_confidence")
    @classmethod
    def validate_maximum_confidence(cls, value: Decimal) -> Decimal:
        return _validate_confidence_decimal(value, field_name="maximum_confidence")


class RecommendationPolicyDecision(CommitteeModel):
    allowed_recommendations: list[InvestmentRecommendation] = Field(default_factory=list)
    disallowed_recommendations: dict[InvestmentRecommendation, str] = Field(default_factory=dict)
    critical_missing_items: list[CommitteeMissingItem] = Field(default_factory=list)
    offer_range: DeterministicOfferRange
    confidence_limit: ConfidencePolicyResult
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_uniqueness(self) -> RecommendationPolicyDecision:
        if len(set(self.allowed_recommendations)) != len(self.allowed_recommendations):
            raise ValueError("allowed_recommendations must not contain duplicates.")
        return self


class CommitteeExecutionMetadata(CommitteeModel):
    request_id: str
    workflow_name: str
    agent_version: str
    prompt_version: str
    input_format_version: str
    recommendation_policy_version: str
    offer_range_policy_version: str
    confidence_policy_version: str
    model: str
    traced: bool = False
    trace_metadata: dict[str, str] = Field(default_factory=dict)
    trace_id: str | None = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    duration_ms: int = 0
    retry_count: int = 0
    validation_status: str
    warning_count: int = 0

    @field_validator("duration_ms", "retry_count", "warning_count")
    @classmethod
    def validate_non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("Execution counters must be non-negative.")
        return value

    @model_validator(mode="after")
    def validate_completed_at(self) -> CommitteeExecutionMetadata:
        if self.completed_at < self.started_at:
            raise ValueError("completed_at must be greater than or equal to started_at.")
        return self


class CommitteeUsageMetadata(CommitteeModel):
    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    response_count: int = 0

    @field_validator(
        "requests",
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "response_count",
    )
    @classmethod
    def validate_non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("Usage counters must be non-negative.")
        return value


class InvestmentCommitteeAnalysisResult(CommitteeModel):
    output: InvestmentCommitteeOutput
    execution_metadata: CommitteeExecutionMetadata
    usage_metadata: CommitteeUsageMetadata
    warnings: list[str] = Field(default_factory=list)
