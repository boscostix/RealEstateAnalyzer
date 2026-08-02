"""Tests for the Property Risk Agent contracts, builders, and guardrails."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.agent_research.evidence import build_property_key
from app.agent_research.exceptions import AgentGuardrailFailureError
from app.agent_research.guardrails import validate_agent_output
from app.agent_research.input_builders import build_property_risk_agent_input
from app.agent_research.models import EvidenceReference, EvidenceSourceType, FindingSeverity
from app.agent_research.risk_models import (
    InspectionPriority,
    RiskCategory,
    RiskFinding,
    SellerQuestion,
    SellerQuestionPriority,
)
from app.agent_research.services import PropertyRiskAgentService
from app.agent_research.versioning import AgentName
from app.models.underwriting import StressTestResult
from tests.agent_sdk_utils import (
    StubAgentRunner,
    make_agent_context,
    make_comparable_agent_output,
    make_listing_agent_output,
    make_neighborhood_agent_output,
    make_property_risk_output,
    make_public_records_agent_output,
    make_underwriting_analysis,
)


def _verified_evidence(property_key: str, field_path: str) -> EvidenceReference:
    return EvidenceReference(
        source_id=f"{property_key}:verified_property",
        source_type=EvidenceSourceType.VERIFIED_PROPERTY,
        field_path=field_path,
    )


def _underwriting_evidence(property_key: str, field_path: str) -> EvidenceReference:
    return EvidenceReference(
        source_id=f"{property_key}:underwriting",
        source_type=EvidenceSourceType.UNDERWRITING,
        field_path=field_path,
    )


def _physical_risk_finding(property_key: str, *, qualified: bool = True) -> RiskFinding:
    summary = (
        "The roof may need further inspection because age is not verified."
        if qualified
        else "The roof is failing and needs full replacement."
    )
    return RiskFinding(
        risk_id="risk-physical-1",
        category=RiskCategory.PHYSICAL_CONDITION,
        title="Roof condition uncertainty",
        summary=summary,
        significance="A roof issue could affect near-term capital planning.",
        severity=FindingSeverity.MEDIUM,
        confidence=Decimal("0.70"),
        evidence=[_verified_evidence(property_key, "verified_property.full_address.final_value")],
        inspection_priority=InspectionPriority.HIGH,
        affected_fields=["roof_type"],
        recommended_next_actions=["Order a licensed roof inspection."],
    )


def _financial_risk_finding(property_key: str, *, supported: bool = True) -> RiskFinding:
    evidence = (
        [
            _underwriting_evidence(
                property_key,
                "underwriting.metrics.dscr",
            )
        ]
        if supported
        else [_verified_evidence(property_key, "verified_property.asking_price.final_value")]
    )
    return RiskFinding(
        risk_id="risk-financial-1",
        category=RiskCategory.FINANCIAL_FRAGILITY,
        title="Stress-test cash flow pressure",
        summary="Stress-test results could push monthly cash flow below target thresholds.",
        significance="Thin cash flow may require larger reserves if adverse assumptions occur.",
        severity=FindingSeverity.HIGH,
        confidence=Decimal("0.78"),
        evidence=evidence,
        affected_fields=["monthly_pre_tax_cash_flow", "dscr"],
        recommended_next_actions=["Review reserve requirements against stress scenarios."],
    )


@pytest.mark.asyncio
async def test_property_risk_input_builder_uses_validated_upstream_outputs() -> None:
    context = make_agent_context(underwriting_result=make_underwriting_analysis())
    stress_test = StressTestResult(
        identifier="rent_down_10",
        description="Rent declines by 10 percent.",
        changed_assumptions={"monthly_rent_delta": Decimal("-0.10")},
        change_in_monthly_cash_flow=Decimal("-250"),
        change_in_annual_cash_flow=Decimal("-3000"),
        change_in_cash_on_cash_return=Decimal("-0.03"),
        cash_flow_remains_positive=False,
        additional_cash_required=Decimal("250"),
        stressed_metrics=context.underwriting_result.metrics,  # type: ignore[union-attr]
        warnings=[],
    )
    context.underwriting_result = context.underwriting_result.model_copy(  # type: ignore[union-attr]
        update={"stress_tests": [stress_test]}
    )
    listing_output = make_listing_agent_output()
    public_records_output = make_public_records_agent_output()
    comparable_output = make_comparable_agent_output()
    neighborhood_output = make_neighborhood_agent_output()

    built = await build_property_risk_agent_input(
        context,
        listing_analysis=listing_output,
        public_records_analysis=public_records_output,
        comparable_analysis=comparable_output,
        neighborhood_analysis=neighborhood_output,
        conflicts=[],
        duplicate_findings=[],
        upstream_data_confidence=Decimal("0.82"),
    )

    assert built.listing_analysis.agent_name == "listing_agent"
    assert built.public_records_analysis.agent_name == "public_records_agent"
    assert built.underwriting_summary is not None
    assert built.underwriting_summary.dscr == Decimal("1.2")
    assert built.stress_tests[0].identifier == "rent_down_10"
    assert built.stress_tests[0].cash_flow_remains_positive is False


@pytest.mark.asyncio
async def test_property_risk_agent_service_runs_with_structured_input() -> None:
    context = make_agent_context(underwriting_result=make_underwriting_analysis())
    property_key = build_property_key(context.verified_property)
    built_input = await build_property_risk_agent_input(
        context,
        listing_analysis=make_listing_agent_output(),
        public_records_analysis=make_public_records_agent_output(),
        comparable_analysis=make_comparable_agent_output(),
        neighborhood_analysis=make_neighborhood_agent_output(),
        conflicts=[],
        duplicate_findings=[],
        upstream_data_confidence=Decimal("0.82"),
    )
    output = make_property_risk_output()
    output.risk_findings = [
        _physical_risk_finding(property_key),
        _financial_risk_finding(property_key),
    ]
    output.seller_questions = [
        SellerQuestion(
            question_id="question-1",
            question="When was the roof last replaced or repaired?",
            priority=SellerQuestionPriority.HIGH,
            rationale="Roof age is not verified in the record.",
            related_risk_ids=["risk-physical-1"],
            evidence=[
                _verified_evidence(
                    property_key,
                    "verified_property.full_address.final_value",
                )
            ],
        )
    ]
    runner = StubAgentRunner(output)
    service = PropertyRiskAgentService(runner=runner)

    result = await service.run(context, built_input=built_input)

    assert result.agent_name == "property_risk_agent"
    assert result.risk_findings[0].category == RiskCategory.PHYSICAL_CONDITION
    assert result.risk_findings[1].category == RiskCategory.FINANCIAL_FRAGILITY


def test_property_risk_guardrail_rejects_unqualified_defect_claims() -> None:
    context = make_agent_context(underwriting_result=make_underwriting_analysis())
    property_key = build_property_key(context.verified_property)
    output = make_property_risk_output()
    output.risk_findings = [_physical_risk_finding(property_key, qualified=False)]

    with pytest.raises(AgentGuardrailFailureError):
        validate_agent_output(agent_name=AgentName.PROPERTY_RISK, output=output, context=context)


def test_property_risk_guardrail_requires_underwriting_evidence_for_financial_fragility() -> None:
    context = make_agent_context(underwriting_result=make_underwriting_analysis())
    property_key = build_property_key(context.verified_property)
    output = make_property_risk_output()
    output.risk_findings = [_financial_risk_finding(property_key, supported=False)]

    with pytest.raises(AgentGuardrailFailureError):
        validate_agent_output(agent_name=AgentName.PROPERTY_RISK, output=output, context=context)


def test_property_risk_guardrail_allows_qualified_physical_and_supported_financial_claims() -> None:
    context = make_agent_context(underwriting_result=make_underwriting_analysis())
    property_key = build_property_key(context.verified_property)
    output = make_property_risk_output()
    output.risk_findings = [
        _physical_risk_finding(property_key),
        _financial_risk_finding(property_key),
    ]
    output.overall_confidence = Decimal("0.80")

    report = validate_agent_output(
        agent_name=AgentName.PROPERTY_RISK,
        output=output,
        context=context,
    )

    assert report.risk is not None
    assert report.risk["unqualified_physical_risk_ids"] == []
    assert report.risk["unsupported_financial_risk_ids"] == []


def test_property_risk_missing_data_can_be_represented_as_risk() -> None:
    property_key = build_property_key(make_agent_context().verified_property)
    output = make_property_risk_output()
    output.risk_findings = [
        RiskFinding(
            risk_id="risk-data-gap-1",
            category=RiskCategory.DATA_GAP,
            title="Permit history gap",
            summary="Permit history may be incomplete because no records were returned.",
            significance="Missing permit evidence could conceal deferred maintenance questions.",
            severity=FindingSeverity.MEDIUM,
            confidence=Decimal("0.66"),
            evidence=[
                _verified_evidence(
                    property_key,
                    "verified_property.full_address.final_value",
                )
            ],
            missing_information=["Permit history"],
            is_missing_data_risk=True,
        )
    ]

    assert output.risk_findings[0].is_missing_data_risk is True
