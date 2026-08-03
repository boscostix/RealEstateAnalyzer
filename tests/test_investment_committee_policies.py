"""Tests for deterministic investment-committee policy helpers."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.agent_research.models import (
    ConflictMateriality,
    ConflictResolutionStatus,
    ConflictValue,
    ResearchConflict,
)
from app.investment_committee.exceptions import (
    ConfidencePolicyViolationError,
    RecommendationPolicyViolationError,
    UnsupportedOfferValueError,
)
from app.investment_committee.models import (
    InvestmentCommitteeInput,
    InvestmentCommitteeOutput,
    InvestmentRecommendation,
    MissingInformationMateriality,
)
from app.investment_committee.policies import (
    build_offer_range,
    build_recommendation_policy,
    classify_missing_information,
    compute_confidence_limit,
    validate_offer_value,
    validate_recommendation,
    validate_recommendation_confidence,
)
from app.models.assumptions import (
    AcquisitionAssumptions,
    AnalysisAssumptions,
    AnalysisPreset,
    ExpenseAssumptions,
    FinancingAssumptions,
    FinancingType,
    IncomeAssumptions,
    TargetAssumptions,
)
from app.models.underwriting import (
    AcquisitionResult,
    ExpenseLineItem,
    FinancingResult,
    IncomeResult,
    InvestmentMetrics,
    MaximumOfferResult,
    OperatingExpenseResult,
    ScenarioResult,
    StressTestResult,
    UnderwritingAnalysis,
)
from tests.agent_sdk_utils import make_verified_property
from tests.test_investment_committee_models import (
    make_agent_research_package,
    make_due_diligence_item,
    make_evidence_reference,
    make_reason,
    make_required_condition,
)


def make_committee_input() -> InvestmentCommitteeInput:
    property_snapshot = make_verified_property()
    assumptions = AnalysisAssumptions(
        purchase_price=Decimal("300000"),
        preset=AnalysisPreset.STANDARD,
        financing=FinancingAssumptions(
            type=FinancingType.CONVENTIONAL,
            down_payment_percent=Decimal("20"),
            interest_rate_percent=Decimal("6.50"),
            loan_term_years=30,
        ),
        acquisition=AcquisitionAssumptions(
            closing_cost_percent=Decimal("3"),
            repairs=Decimal("5000"),
            initial_reserves=Decimal("5000"),
        ),
        income=IncomeAssumptions(
            monthly_rent=Decimal("2200"),
            vacancy_percent=Decimal("5"),
        ),
        expenses=ExpenseAssumptions(
            annual_property_taxes=Decimal("4800"),
            annual_insurance=Decimal("1800"),
            annual_hoa=Decimal("0"),
            management_percent=Decimal("8"),
            maintenance_percent=Decimal("5"),
            capex_percent=Decimal("5"),
        ),
        targets=TargetAssumptions(
            monthly_cash_flow=Decimal("0"),
            dscr=Decimal("1.00"),
        ),
    )
    financing = FinancingResult(
        financing_type=FinancingType.CONVENTIONAL,
        original_loan_balance=Decimal("240000"),
        monthly_principal_interest=Decimal("1516"),
        annual_debt_service=Decimal("18192"),
        monthly_mortgage_insurance=Decimal("0"),
        total_monthly_debt_payment=Decimal("1516"),
    )
    operating_expenses = OperatingExpenseResult(
        property_taxes=ExpenseLineItem(monthly=Decimal("400"), annual=Decimal("4800")),
        insurance=ExpenseLineItem(monthly=Decimal("150"), annual=Decimal("1800")),
        hoa=ExpenseLineItem(monthly=Decimal("0"), annual=Decimal("0")),
        management=ExpenseLineItem(monthly=Decimal("176"), annual=Decimal("2112")),
        maintenance=ExpenseLineItem(monthly=Decimal("110"), annual=Decimal("1320")),
        capital_expenditures=ExpenseLineItem(monthly=Decimal("110"), annual=Decimal("1320")),
        leasing_turnover=ExpenseLineItem(monthly=Decimal("0"), annual=Decimal("0")),
        utilities=ExpenseLineItem(monthly=Decimal("0"), annual=Decimal("0")),
        landscaping=ExpenseLineItem(monthly=Decimal("0"), annual=Decimal("0")),
        pest_control=ExpenseLineItem(monthly=Decimal("0"), annual=Decimal("0")),
        other=ExpenseLineItem(monthly=Decimal("0"), annual=Decimal("0")),
        total_monthly_operating_expenses=Decimal("946"),
        total_annual_operating_expenses=Decimal("11352"),
    )
    metrics = InvestmentMetrics(
        noi=Decimal("13728"),
        monthly_pre_tax_cash_flow=Decimal("250"),
        annual_pre_tax_cash_flow=Decimal("3000"),
        cap_rate=Decimal("0.05"),
        cash_on_cash_return=Decimal("0.05"),
        dscr=Decimal("1.20"),
        gross_rent_multiplier=None,
        operating_expense_ratio=None,
        break_even_occupancy=None,
        rent_to_price_ratio=None,
    )
    income = IncomeResult(
        monthly_scheduled_rent=Decimal("2200"),
        monthly_other_income=Decimal("0"),
        monthly_gross_scheduled_income=Decimal("2200"),
        monthly_vacancy_loss=Decimal("110"),
        monthly_effective_gross_income=Decimal("2090"),
        annual_gross_scheduled_income=Decimal("26400"),
        annual_vacancy_loss=Decimal("1320"),
        annual_effective_gross_income=Decimal("25080"),
    )
    acquisition = AcquisitionResult(
        purchase_price=Decimal("300000"),
        down_payment=Decimal("60000"),
        base_loan_amount=Decimal("240000"),
        financing_points=Decimal("0"),
        lender_fees=Decimal("0"),
        closing_costs=Decimal("9000"),
        repairs=Decimal("5000"),
        initial_reserves=Decimal("5000"),
        other_acquisition_costs=Decimal("0"),
        total_cash_required_at_closing=Decimal("79000"),
        total_project_cost=Decimal("319000"),
    )
    conservative_metrics = metrics.model_copy(
        update={
            "monthly_pre_tax_cash_flow": Decimal("100"),
            "dscr": Decimal("1.10"),
        }
    )
    conservative = ScenarioResult(
        name="conservative",
        base_assumptions=assumptions,
        adjustments={},
        final_assumptions_used=assumptions,
        acquisition=acquisition,
        financing=financing,
        income=income,
        operating_expenses=operating_expenses,
        metrics=conservative_metrics,
        warnings=[],
    )
    underwriting = UnderwritingAnalysis(
        property=property_snapshot,
        assumptions_used=assumptions,
        acquisition=acquisition,
        financing=financing,
        income=income,
        operating_expenses=operating_expenses,
        metrics=metrics,
        maximum_offer=MaximumOfferResult(
            break_even_cash_flow_price=Decimal("295000"),
            target_monthly_cash_flow_price=Decimal("280000"),
            target_cap_rate_price=None,
            target_cash_on_cash_price=None,
            target_dscr_price=Decimal("285000"),
            binding_maximum_price=Decimal("280000"),
            asking_price_gap=Decimal("20000"),
            asking_price_satisfies_break_even=False,
            asking_price_satisfies_target_monthly_cash_flow=False,
            asking_price_satisfies_target_cap_rate=None,
            asking_price_satisfies_target_cash_on_cash=None,
            asking_price_satisfies_target_dscr=False,
            warnings=[],
        ),
        scenarios=[conservative],
        stress_tests=[
            StressTestResult(
                identifier="rates_up",
                description="Rate increase sensitivity",
                changed_assumptions={"interest_rate_percent": Decimal("7.5")},
                change_in_monthly_cash_flow=Decimal("-75"),
                change_in_annual_cash_flow=Decimal("-900"),
                change_in_cash_on_cash_return=Decimal("-0.01"),
                cash_flow_remains_positive=True,
                additional_cash_required=Decimal("0"),
                stressed_metrics=metrics.model_copy(
                    update={"monthly_pre_tax_cash_flow": Decimal("175")}
                ),
                warnings=[],
            )
        ],
        warnings=[],
    )
    return InvestmentCommitteeInput(
        property=property_snapshot,
        assumptions=underwriting.assumptions_used,
        underwriting=underwriting,
        agent_research=make_agent_research_package(),
    )


def make_output(*, confidence: Decimal) -> InvestmentCommitteeOutput:
    return InvestmentCommitteeOutput(
        recommendation=InvestmentRecommendation.NEGOTIATE,
        recommendation_summary="Further negotiation is warranted.",
        recommendation_confidence=confidence,
        asking_price=Decimal("300000"),
        investment_thesis="The deal could work below ask.",
        strongest_upside="Solid baseline income at a lower basis.",
        strongest_downside="Current price exceeds the supported threshold.",
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


def test_missing_information_is_classified_deterministically() -> None:
    item = classify_missing_information("Expected rent is unsupported by rental comps.")

    assert item.materiality == MissingInformationMateriality.DECISION_CRITICAL
    assert item.blocks_recommendation is True


def test_offer_range_uses_only_deterministic_thresholds() -> None:
    committee_input = make_committee_input()

    offer_range = build_offer_range(committee_input)

    assert offer_range.valid_threshold_exists is True
    assert offer_range.supported_offer_low == Decimal("280000")
    assert offer_range.supported_offer_high == Decimal("295000")
    assert Decimal("280000") in offer_range.allowed_values
    assert Decimal("295000") in offer_range.allowed_values


def test_validate_offer_value_rejects_unsupported_number() -> None:
    committee_input = make_committee_input()
    offer_range = build_offer_range(committee_input)

    with pytest.raises(UnsupportedOfferValueError):
        validate_offer_value(Decimal("281111"), offer_range)


def test_confidence_limit_drops_for_unresolved_conflicts_and_missing_information() -> None:
    committee_input = make_committee_input()
    committee_input.agent_research = committee_input.agent_research.model_copy(
        update={
            "missing_information": ["Expected rent is unsupported", "Insurance quote is missing"],
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
            ],
        }
    )

    result = compute_confidence_limit(committee_input)

    assert result.maximum_confidence < Decimal("0.80")
    assert any(reason.startswith("decision_critical_missing:") for reason in result.reasons)
    assert any(reason.startswith("unresolved_high_conflict:") for reason in result.reasons)


def test_recommendation_policy_disallows_strong_buy_with_high_conflict() -> None:
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

    policy = build_recommendation_policy(committee_input)

    assert InvestmentRecommendation.STRONG_BUY not in policy.allowed_recommendations
    with pytest.raises(RecommendationPolicyViolationError):
        validate_recommendation(InvestmentRecommendation.STRONG_BUY, policy)


def test_recommendation_policy_requires_threshold_for_buy_only_below() -> None:
    committee_input = make_committee_input()
    committee_input.underwriting = committee_input.underwriting.model_copy(
        update={
            "maximum_offer": committee_input.underwriting.maximum_offer.model_copy(
                update={
                    "break_even_cash_flow_price": None,
                    "target_monthly_cash_flow_price": None,
                    "target_cap_rate_price": None,
                    "target_cash_on_cash_price": None,
                    "target_dscr_price": None,
                    "binding_maximum_price": None,
                }
            )
        }
    )

    policy = build_recommendation_policy(committee_input)

    assert InvestmentRecommendation.BUY_ONLY_BELOW not in policy.allowed_recommendations


def test_validate_recommendation_confidence_enforces_deterministic_cap() -> None:
    committee_input = make_committee_input()
    policy = build_recommendation_policy(committee_input)
    output = make_output(confidence=policy.confidence_limit.maximum_confidence + Decimal("0.01"))

    with pytest.raises(ConfidencePolicyViolationError):
        validate_recommendation_confidence(output, policy)
