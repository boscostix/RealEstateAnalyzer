"""Tests for investment-committee output validation and enforcement."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.agent_research.models import (
    ConflictMateriality,
    ConflictResolutionStatus,
    ConflictValue,
    EvidenceReference,
    EvidenceSourceType,
    FindingSeverity,
    ResearchConflict,
)
from app.investment_committee.exceptions import (
    CommitteeOutputValidationError,
    ConfidencePolicyViolationError,
    UnsupportedOfferValueError,
)
from app.investment_committee.input_builders import build_committee_model_input
from app.investment_committee.models import (
    CommitteeMissingItem,
    CommitteeRisk,
    DueDiligenceItem,
    DueDiligencePriority,
    DueDiligenceTiming,
    InvestmentRecommendation,
    MissingInformationMateriality,
    NegotiationPoint,
    OfferRangeBasis,
    ReasonImportance,
    RequiredCondition,
    RiskProbability,
)
from app.investment_committee.validation import validate_and_enforce_output
from tests.test_investment_committee_agent import make_committee_output
from tests.test_investment_committee_models import make_evidence_reference
from tests.test_investment_committee_policies import make_committee_input


def _unsupported_evidence() -> EvidenceReference:
    return EvidenceReference(
        source_id="property:other:verified_property",
        source_type=EvidenceSourceType.VERIFIED_PROPERTY,
        field_path="verified_property.asking_price.final_value",
    )


def test_validate_output_rejects_unsupported_evidence() -> None:
    committee_input = make_committee_input()
    prepared = build_committee_model_input(committee_input)
    output = make_committee_output().model_copy(
        update={
            "reasons_to_proceed": [
                make_committee_output()
                .reasons_to_proceed[0]
                .model_copy(update={"evidence": [_unsupported_evidence()]})
            ]
        }
    )

    with pytest.raises(CommitteeOutputValidationError):
        validate_and_enforce_output(output, prepared_input=prepared)


def test_validate_output_rejects_unsupported_offer_values() -> None:
    committee_input = make_committee_input()
    prepared = build_committee_model_input(committee_input)
    output = make_committee_output().model_copy(
        update={
            "supported_offer_low": Decimal("281111"),
            "supported_offer_high": Decimal("281111"),
            "recommended_offer_basis": [
                OfferRangeBasis(
                    value=Decimal("281111"),
                    source_metric="binding_maximum_price",
                    source_path="underwriting.maximum_offer.binding_maximum_price",
                    description="Invalid unsupported value.",
                )
            ],
        }
    )

    with pytest.raises(UnsupportedOfferValueError):
        validate_and_enforce_output(output, prepared_input=prepared)


def test_validate_output_downgrades_policy_invalid_recommendation() -> None:
    committee_input = make_committee_input()
    committee_input.agent_research = committee_input.agent_research.model_copy(
        update={"missing_information": ["Expected rent is unsupported"]}
    )
    prepared = build_committee_model_input(committee_input)
    output = make_committee_output().model_copy(
        update={
            "recommendation": InvestmentRecommendation.BUY,
            "recommendation_confidence": Decimal("0.35"),
            "missing_information": [
                CommitteeMissingItem(
                    item="Expected rent is unsupported",
                    materiality=MissingInformationMateriality.DECISION_CRITICAL,
                    importance=ReasonImportance.DECISIVE,
                    reason_needed="Rent support is required to evaluate income durability.",
                    decision_impact=(
                        "Without supported rent, the committee cannot validate returns."
                    ),
                    recommended_source="Rental comparable research",
                    blocks_recommendation=True,
                )
            ],
        }
    )

    validated = validate_and_enforce_output(output, prepared_input=prepared)

    assert validated.recommendation == InvestmentRecommendation.INSUFFICIENT_INFORMATION
    assert any(item.startswith("recommendation_downgraded:") for item in validated.warnings)


def test_validate_output_rejects_confidence_above_maximum() -> None:
    committee_input = make_committee_input()
    committee_input.agent_research = committee_input.agent_research.model_copy(
        update={"missing_information": ["Expected rent is unsupported"]}
    )
    prepared = build_committee_model_input(committee_input)
    output = make_committee_output().model_copy(
        update={"recommendation_confidence": Decimal("0.99")}
    )

    with pytest.raises(ConfidencePolicyViolationError):
        validate_and_enforce_output(output, prepared_input=prepared)


def test_validate_output_rejects_changed_asking_price() -> None:
    committee_input = make_committee_input()
    prepared = build_committee_model_input(committee_input)
    output = make_committee_output().model_copy(update={"asking_price": Decimal("299999")})

    with pytest.raises(CommitteeOutputValidationError):
        validate_and_enforce_output(output, prepared_input=prepared)


def test_validate_output_rejects_disappearing_high_conflict() -> None:
    committee_input = make_committee_input()
    committee_input.agent_research = committee_input.agent_research.model_copy(
        update={
            "conflicts": [
                ResearchConflict(
                    conflict_id="conflict-1",
                    field_or_topic="year_built",
                    values=[
                        ConflictValue(
                            value=1999,
                            source_id="verified_property",
                            source_type="verified_property",
                            confidence=Decimal("1.0"),
                        ),
                        ConflictValue(
                            value=2001,
                            source_id="public_records",
                            source_type="public_records",
                            confidence=Decimal("0.8"),
                        ),
                    ],
                    materiality=ConflictMateriality.HIGH,
                    resolution_status=ConflictResolutionStatus.UNRESOLVED,
                    requires_user_review=True,
                )
            ]
        }
    )
    prepared = build_committee_model_input(committee_input)
    output = make_committee_output().model_copy(
        update={
            "unresolved_conflicts": [],
            "recommendation_confidence": Decimal("0.35"),
        }
    )

    with pytest.raises(CommitteeOutputValidationError):
        validate_and_enforce_output(output, prepared_input=prepared)


def test_validate_output_rejects_disappearing_decision_critical_missing_information() -> None:
    committee_input = make_committee_input()
    committee_input.agent_research = committee_input.agent_research.model_copy(
        update={"missing_information": ["Expected rent is unsupported"]}
    )
    prepared = build_committee_model_input(committee_input)
    output = make_committee_output().model_copy(
        update={
            "missing_information": [],
            "recommendation_confidence": Decimal("0.35"),
        }
    )

    with pytest.raises(CommitteeOutputValidationError):
        validate_and_enforce_output(output, prepared_input=prepared)


def test_validate_output_rejects_prohibited_language() -> None:
    committee_input = make_committee_input()
    prepared = build_committee_model_input(committee_input)
    output = make_committee_output().model_copy(
        update={"recommendation_summary": "This outcome is guaranteed with no risk."}
    )

    with pytest.raises(CommitteeOutputValidationError):
        validate_and_enforce_output(output, prepared_input=prepared)


def test_validate_output_rejects_generic_due_diligence() -> None:
    committee_input = make_committee_input()
    prepared = build_committee_model_input(committee_input)
    output = make_committee_output().model_copy(
        update={
            "due_diligence_checklist": [
                DueDiligenceItem(
                    category="general",
                    action="Do more research on the property.",
                    reason="Further due diligence is needed.",
                    priority=DueDiligencePriority.MEDIUM,
                    timing=DueDiligenceTiming.DURING_OPTION_PERIOD,
                    evidence=[make_evidence_reference()],
                )
            ]
        }
    )

    with pytest.raises(CommitteeOutputValidationError):
        validate_and_enforce_output(output, prepared_input=prepared)


def test_validate_output_rejects_low_priority_critical_due_diligence() -> None:
    committee_input = make_committee_input()
    committee_input.agent_research = committee_input.agent_research.model_copy(
        update={"missing_information": ["Expected rent is unsupported"]}
    )
    prepared = build_committee_model_input(committee_input)
    output = make_committee_output().model_copy(
        update={
            "recommendation_confidence": Decimal("0.35"),
            "missing_information": [
                CommitteeMissingItem(
                    item="Expected rent is unsupported",
                    materiality=MissingInformationMateriality.DECISION_CRITICAL,
                    importance=ReasonImportance.DECISIVE,
                    reason_needed="Expected rent support is missing.",
                    decision_impact="Expected rent uncertainty blocks the return decision.",
                    recommended_source="Rental comparable research",
                    blocks_recommendation=True,
                )
            ],
            "due_diligence_checklist": [
                DueDiligenceItem(
                    category="rent",
                    action="Verify expected rent with rental comparable support.",
                    reason="Expected rent remains unsupported.",
                    priority=DueDiligencePriority.LOW,
                    timing=DueDiligenceTiming.AFTER_PURCHASE,
                    evidence=[make_evidence_reference()],
                )
            ],
        }
    )

    with pytest.raises(CommitteeOutputValidationError):
        validate_and_enforce_output(output, prepared_input=prepared)


def test_validate_output_rejects_unsupported_negotiation_value() -> None:
    committee_input = make_committee_input()
    prepared = build_committee_model_input(committee_input)
    output = make_committee_output().model_copy(
        update={
            "negotiation_points": [
                NegotiationPoint(
                    issue="Asking price exceeds the binding maximum price.",
                    negotiation_request="Request a purchase price reduction to the supported cap.",
                    rationale="The binding maximum price is lower than the current ask.",
                    evidence=[make_evidence_reference()],
                    estimated_value=Decimal("12345"),
                )
            ]
        }
    )

    with pytest.raises(UnsupportedOfferValueError):
        validate_and_enforce_output(output, prepared_input=prepared)


def test_validate_output_rejects_generic_condition_before_offer() -> None:
    committee_input = make_committee_input()
    prepared = build_committee_model_input(committee_input)
    output = make_committee_output().model_copy(
        update={"conditions_before_offer": ["Complete further due diligence before offering."]}
    )

    with pytest.raises(CommitteeOutputValidationError):
        validate_and_enforce_output(output, prepared_input=prepared)


def test_validate_output_rejects_non_measurable_required_condition() -> None:
    committee_input = make_committee_input()
    prepared = build_committee_model_input(committee_input)
    output = make_committee_output().model_copy(
        update={
            "what_must_be_true": [
                RequiredCondition(
                    condition="The deal must make sense overall.",
                    current_status="unknown",
                    threshold_or_requirement="Be acceptable.",
                    evidence=[make_evidence_reference()],
                    consequence_if_false="The investment would be weaker.",
                )
            ]
        }
    )

    with pytest.raises(CommitteeOutputValidationError):
        validate_and_enforce_output(output, prepared_input=prepared)


def test_validate_output_rejects_generic_missing_information_impact() -> None:
    committee_input = make_committee_input()
    committee_input.agent_research = committee_input.agent_research.model_copy(
        update={"missing_information": ["Expected rent is unsupported"]}
    )
    prepared = build_committee_model_input(committee_input)
    output = make_committee_output().model_copy(
        update={
            "recommendation_confidence": Decimal("0.35"),
            "missing_information": [
                CommitteeMissingItem(
                    item="Expected rent is unsupported",
                    materiality=MissingInformationMateriality.DECISION_CRITICAL,
                    importance=ReasonImportance.DECISIVE,
                    reason_needed="Need more information.",
                    decision_impact="It could matter to the decision.",
                    recommended_source="Rental comparable research",
                    blocks_recommendation=True,
                )
            ],
        }
    )

    with pytest.raises(CommitteeOutputValidationError):
        validate_and_enforce_output(output, prepared_input=prepared)


def test_validate_output_rejects_generic_recommendation_language() -> None:
    committee_input = make_committee_input()
    prepared = build_committee_model_input(committee_input)
    output = make_committee_output().model_copy(
        update={"recommendation_summary": "Further due diligence is needed before any decision."}
    )

    with pytest.raises(CommitteeOutputValidationError):
        validate_and_enforce_output(output, prepared_input=prepared)


def test_validate_output_returns_confidence_reasons_and_sorted_risks() -> None:
    committee_input = make_committee_input()
    prepared = build_committee_model_input(committee_input)
    output = make_committee_output().model_copy(
        update={
            "material_risks": [
                CommitteeRisk(
                    category="pricing",
                    title="Moderate pricing gap",
                    explanation="The ask is above the deterministic threshold.",
                    severity=FindingSeverity.MEDIUM,
                    probability=RiskProbability.HIGH,
                    evidence=[make_evidence_reference()],
                    blocks_investment=False,
                ),
                CommitteeRisk(
                    category="cash_flow",
                    title="Critical downside case",
                    explanation="A small rent miss would materially compress returns.",
                    severity=FindingSeverity.CRITICAL,
                    probability=RiskProbability.MEDIUM,
                    evidence=[make_evidence_reference()],
                    blocks_investment=True,
                ),
            ]
        }
    )

    validated = validate_and_enforce_output(output, prepared_input=prepared)

    assert validated.recommendation_confidence_reasons == prepared.policy.confidence_limit.reasons
    assert [risk.title for risk in validated.material_risks] == [
        "Critical downside case",
        "Moderate pricing gap",
    ]
