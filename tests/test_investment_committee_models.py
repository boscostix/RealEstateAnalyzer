"""Tests for investment-committee models and strict validation."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.agent_research.models import (
    EvidenceReference,
    EvidenceSourceType,
    FindingSeverity,
    UnifiedAgentResearchPackage,
)
from app.investment_committee.models import (
    CommitteeExecutionMetadata,
    CommitteeReason,
    CommitteeRisk,
    DueDiligenceItem,
    DueDiligencePriority,
    DueDiligenceTiming,
    InvestmentCommitteeInput,
    InvestmentCommitteeOutput,
    InvestmentRecommendation,
    OfferRangeBasis,
    ReasonImportance,
    RequiredCondition,
    RiskProbability,
)
from app.models.underwriting import ScenarioResult
from app.models.verification import VerifiedPropertySnapshot
from tests.agent_sdk_utils import (
    make_agent_output,
    make_execution_metadata,
    make_underwriting_analysis,
    make_verified_property,
)


def make_evidence_reference() -> EvidenceReference:
    return EvidenceReference(
        source_id="verified_property",
        source_type=EvidenceSourceType.VERIFIED_PROPERTY,
        field_path="verified_property.asking_price.final_value",
    )


def make_agent_research_package() -> UnifiedAgentResearchPackage:
    output = make_agent_output()
    return UnifiedAgentResearchPackage(
        listing_analysis=output,
        public_records_analysis=make_agent_output("public_records_agent"),
        comparable_analysis=make_agent_output("comparable_agent"),
        neighborhood_analysis=make_agent_output("neighborhood_agent"),
        risk_analysis=make_agent_output("property_risk_agent"),
        consolidated_findings=[],
        conflicts=[],
        duplicate_findings=[],
        missing_information=[],
        due_diligence_questions=[],
        evidence_index=[make_evidence_reference()],
        overall_data_confidence=Decimal("0.80"),
        execution_metadata=make_execution_metadata(),
    )


def make_committee_input(
    *,
    property_snapshot: VerifiedPropertySnapshot | None = None,
) -> InvestmentCommitteeInput:
    property_snapshot = property_snapshot or make_verified_property()
    underwriting = make_underwriting_analysis()
    conservative = ScenarioResult(
        name="conservative",
        base_assumptions=underwriting.assumptions_used,
        adjustments={},
        final_assumptions_used=underwriting.assumptions_used,
        acquisition=underwriting.acquisition,
        financing=underwriting.financing,
        income=underwriting.income,
        operating_expenses=underwriting.operating_expenses,
        metrics=underwriting.metrics,
        warnings=[],
    )
    underwriting = underwriting.model_copy(
        update={
            "property": property_snapshot,
            "scenarios": [conservative],
        }
    )
    return InvestmentCommitteeInput(
        property=property_snapshot,
        assumptions=underwriting.assumptions_used,
        underwriting=underwriting,
        agent_research=make_agent_research_package(),
    )


def make_reason() -> CommitteeReason:
    return CommitteeReason(
        title="Supported offer",
        explanation="The asking price is supported by deterministic thresholds.",
        importance=ReasonImportance.HIGH,
        evidence=[make_evidence_reference()],
        affected_metrics=["binding_maximum_price"],
    )


def make_due_diligence_item() -> DueDiligenceItem:
    return DueDiligenceItem(
        category="pricing",
        action="Confirm the seller will accept an offer at or below the binding maximum price.",
        reason="The asking price exceeds the supported deterministic offer threshold.",
        priority=DueDiligencePriority.HIGH,
        timing=DueDiligenceTiming.BEFORE_OFFER,
        evidence=[make_evidence_reference()],
    )


def make_required_condition() -> RequiredCondition:
    return RequiredCondition(
        condition="Monthly rent must hold at the underwritten level.",
        current_status="unverified",
        threshold_or_requirement="At least $2,200 per month.",
        evidence=[make_evidence_reference()],
        consequence_if_false="Cash flow would compress below the modeled case.",
    )


def test_committee_input_rejects_mismatched_source_url() -> None:
    property_snapshot = make_verified_property()
    underwriting = make_underwriting_analysis().model_copy(
        update={
            "property": make_verified_property().model_copy(
                update={"source_url": "https://example.com/other-property"}
            )
        }
    )
    with pytest.raises(ValidationError):
        InvestmentCommitteeInput(
            property=property_snapshot,
            assumptions=underwriting.assumptions_used,
            underwriting=underwriting,
            agent_research=make_agent_research_package(),
        )


def test_committee_output_rejects_buy_only_below_without_threshold() -> None:
    with pytest.raises(ValidationError):
        InvestmentCommitteeOutput(
            recommendation=InvestmentRecommendation.BUY_ONLY_BELOW,
            recommendation_summary="Only works below ask.",
            recommendation_confidence=Decimal("0.70"),
            asking_price=Decimal("300000"),
            investment_thesis="The property may work at a lower price.",
            strongest_upside="Below-market asking price if negotiated lower.",
            strongest_downside="Current price is unsupported.",
            reasons_to_proceed=[make_reason()],
            reasons_not_to_proceed=[make_reason()],
            key_assumptions=[],
            fragile_assumptions=[],
            material_risks=[],
            missing_information=[],
            unresolved_conflicts=[],
            what_must_be_true=[make_required_condition()],
            due_diligence_checklist=[make_due_diligence_item()],
            negotiation_points=[],
            conditions_before_offer=[],
            conditions_before_closing=[],
            evidence_references=[make_evidence_reference()],
        )


def test_committee_output_accepts_deterministic_offer_basis() -> None:
    output = InvestmentCommitteeOutput(
        recommendation=InvestmentRecommendation.BUY_ONLY_BELOW,
        recommendation_summary="Only works below ask.",
        recommendation_confidence=Decimal("0.70"),
        asking_price=Decimal("300000"),
        supported_offer_low=Decimal("250000"),
        supported_offer_high=Decimal("280000"),
        recommended_offer_basis=[
            OfferRangeBasis(
                value=Decimal("250000"),
                source_metric="binding_maximum_price",
                source_path="underwriting.maximum_offer.binding_maximum_price",
                description="Most restrictive deterministic ceiling.",
            ),
            OfferRangeBasis(
                value=Decimal("280000"),
                source_metric="break_even_cash_flow_price",
                source_path="underwriting.maximum_offer.break_even_cash_flow_price",
                description="Break-even cash-flow ceiling.",
            ),
        ],
        investment_thesis="The property may work at a lower price.",
        strongest_upside="Could work if acquired below the binding threshold.",
        strongest_downside="Current price is unsupported.",
        reasons_to_proceed=[make_reason()],
        reasons_not_to_proceed=[make_reason()],
        key_assumptions=[],
        fragile_assumptions=[],
        material_risks=[],
        missing_information=[],
        unresolved_conflicts=[],
        what_must_be_true=[make_required_condition()],
        due_diligence_checklist=[make_due_diligence_item()],
        negotiation_points=[],
        conditions_before_offer=[],
        conditions_before_closing=[],
        evidence_references=[make_evidence_reference()],
    )

    assert output.supported_offer_high == Decimal("280000")


def test_committee_reason_requires_evidence() -> None:
    with pytest.raises(ValidationError):
        CommitteeReason(
            title="Unsupported",
            explanation="No evidence attached.",
            importance=ReasonImportance.HIGH,
            evidence=[],
        )


def test_committee_risk_requires_evidence() -> None:
    with pytest.raises(ValidationError):
        CommitteeRisk(
            category="condition",
            title="Major issue",
            explanation="A material issue exists.",
            severity=FindingSeverity.HIGH,
            probability=RiskProbability.MEDIUM,
            evidence=[],
            blocks_investment=True,
        )


def test_committee_execution_metadata_rejects_negative_duration() -> None:
    started_at = datetime.now(UTC)
    with pytest.raises(ValidationError):
        CommitteeExecutionMetadata(
            agent_version="v1",
            prompt_version="v1",
            input_format_version="v1",
            recommendation_policy_version="v1",
            offer_range_policy_version="v1",
            confidence_policy_version="v1",
            model="gpt-5-mini",
            started_at=started_at,
            completed_at=started_at,
            duration_ms=-1,
            validation_status="passed",
        )
