"""Shared test builders for persistence-layer tests."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from app.agent_research.models import (
    AgentExecutionMetadata,
    UnifiedAgentResearchPackage,
)
from app.investment_committee.models import InvestmentCommitteeOutput, InvestmentRecommendation
from app.models.assumptions import (
    AcquisitionAssumptions,
    AnalysisAssumptions,
    ExpenseAssumptions,
    FinancingAssumptions,
    FinancingType,
    IncomeAssumptions,
)
from app.models.property import Address, NormalizedProperty
from app.models.research_package import (
    ResearchPackage,
    ResearchPackageMetadata,
)
from app.models.underwriting import (
    AcquisitionResult,
    ExpenseLineItem,
    FinancingResult,
    IncomeResult,
    InvestmentMetrics,
    MaximumOfferResult,
    OperatingExpenseResult,
    UnderwritingAnalysis,
)
from app.models.verification import VerificationStatus, VerifiedField, VerifiedPropertySnapshot


def build_normalized_property(asking_price: str = "450000") -> NormalizedProperty:
    return NormalizedProperty(
        source_url="https://www.zillow.com/homedetails/example",
        provider="zillow",
        listing_id="listing-123",
        address=Address(
            street="123 Main St",
            city="Dallas",
            state="TX",
            postal_code="75001",
            full_address="123 Main St, Dallas, TX 75001",
        ),
        latitude=Decimal("32.7767000"),
        longitude=Decimal("-96.7970000"),
        asking_price=Decimal(asking_price),
        bedrooms=Decimal("3"),
        bathrooms=Decimal("2"),
        square_feet=1500,
        lot_square_feet=6000,
        year_built=1995,
        annual_property_tax=Decimal("4200"),
        annual_hoa=Decimal("0"),
        property_type="single_family",
    )


def build_verified_property(asking_price: str = "445000") -> VerifiedPropertySnapshot:
    return VerifiedPropertySnapshot(
        source_url="https://www.zillow.com/homedetails/example",
        provider="zillow",
        full_address=VerifiedField[str](
            extracted_value="123 Main St, Dallas, TX 75001",
            final_value="123 Main St, Dallas, TX 75001",
            status=VerificationStatus.VERIFIED,
            source="hasdata_api",
            confidence=Decimal("0.99"),
        ),
        asking_price=VerifiedField[Decimal](
            extracted_value=Decimal("450000"),
            final_value=Decimal(asking_price),
            status=VerificationStatus.CORRECTED,
            source="hasdata_api",
            confidence=Decimal("0.99"),
            user_modified=True,
        ),
        bedrooms=VerifiedField[Decimal](
            extracted_value=Decimal("3"),
            final_value=Decimal("3"),
            status=VerificationStatus.VERIFIED,
        ),
        bathrooms=VerifiedField[Decimal](
            extracted_value=Decimal("2"),
            final_value=Decimal("2"),
            status=VerificationStatus.VERIFIED,
        ),
        square_feet=VerifiedField[int](
            extracted_value=1500,
            final_value=1500,
            status=VerificationStatus.VERIFIED,
        ),
        lot_square_feet=VerifiedField[int](
            extracted_value=6000,
            final_value=6000,
            status=VerificationStatus.VERIFIED,
        ),
        year_built=VerifiedField[int](
            extracted_value=1995,
            final_value=1995,
            status=VerificationStatus.VERIFIED,
        ),
        annual_property_tax=VerifiedField[Decimal](
            extracted_value=Decimal("4200"),
            final_value=Decimal("4200"),
            status=VerificationStatus.VERIFIED,
        ),
        annual_hoa=VerifiedField[Decimal](
            extracted_value=Decimal("0"),
            final_value=Decimal("0"),
            status=VerificationStatus.VERIFIED,
        ),
        property_type=VerifiedField[str](
            extracted_value="single_family",
            final_value="single_family",
            status=VerificationStatus.VERIFIED,
        ),
    )


def build_assumptions(purchase_price: str = "440000") -> AnalysisAssumptions:
    return AnalysisAssumptions(
        purchase_price=Decimal(purchase_price),
        financing=FinancingAssumptions(
            type=FinancingType.CONVENTIONAL,
            down_payment_percent=Decimal("20"),
            interest_rate_percent=Decimal("6.25"),
            loan_term_years=30,
        ),
        acquisition=AcquisitionAssumptions(),
        income=IncomeAssumptions(
            monthly_rent=Decimal("3200"),
            vacancy_percent=Decimal("5"),
        ),
        expenses=ExpenseAssumptions(
            annual_property_taxes=Decimal("4200"),
            annual_insurance=Decimal("1800"),
            annual_hoa=Decimal("0"),
        ),
    )


def build_underwriting_result(
    property_snapshot: VerifiedPropertySnapshot,
    assumptions: AnalysisAssumptions,
) -> UnderwritingAnalysis:
    zero = Decimal("0")
    return UnderwritingAnalysis(
        property=property_snapshot,
        assumptions_used=assumptions,
        acquisition=AcquisitionResult(
            purchase_price=assumptions.purchase_price,
            down_payment=Decimal("88000"),
            base_loan_amount=Decimal("352000"),
            financing_points=zero,
            lender_fees=zero,
            closing_costs=zero,
            repairs=zero,
            initial_reserves=zero,
            other_acquisition_costs=zero,
            total_cash_required_at_closing=Decimal("88000"),
            total_project_cost=assumptions.purchase_price,
        ),
        financing=FinancingResult(
            financing_type=FinancingType.CONVENTIONAL,
            original_loan_balance=Decimal("352000"),
            monthly_principal_interest=Decimal("2167.92"),
            annual_debt_service=Decimal("26015.04"),
            monthly_mortgage_insurance=zero,
            total_monthly_debt_payment=Decimal("2167.92"),
        ),
        income=IncomeResult(
            monthly_scheduled_rent=Decimal("3200"),
            monthly_other_income=zero,
            monthly_gross_scheduled_income=Decimal("3200"),
            monthly_vacancy_loss=Decimal("160"),
            monthly_effective_gross_income=Decimal("3040"),
            annual_gross_scheduled_income=Decimal("38400"),
            annual_vacancy_loss=Decimal("1920"),
            annual_effective_gross_income=Decimal("36480"),
        ),
        operating_expenses=OperatingExpenseResult(
            property_taxes=ExpenseLineItem(monthly=Decimal("350"), annual=Decimal("4200")),
            insurance=ExpenseLineItem(monthly=Decimal("150"), annual=Decimal("1800")),
            hoa=ExpenseLineItem(monthly=zero, annual=zero),
            management=ExpenseLineItem(monthly=zero, annual=zero),
            maintenance=ExpenseLineItem(monthly=zero, annual=zero),
            capital_expenditures=ExpenseLineItem(monthly=zero, annual=zero),
            leasing_turnover=ExpenseLineItem(monthly=zero, annual=zero),
            utilities=ExpenseLineItem(monthly=zero, annual=zero),
            landscaping=ExpenseLineItem(monthly=zero, annual=zero),
            pest_control=ExpenseLineItem(monthly=zero, annual=zero),
            other=ExpenseLineItem(monthly=zero, annual=zero),
            total_monthly_operating_expenses=Decimal("500"),
            total_annual_operating_expenses=Decimal("6000"),
        ),
        metrics=InvestmentMetrics(
            noi=Decimal("30480"),
            monthly_pre_tax_cash_flow=Decimal("372.08"),
            annual_pre_tax_cash_flow=Decimal("4464.96"),
            cap_rate=Decimal("0.0693"),
            cash_on_cash_return=Decimal("0.0507"),
            dscr=Decimal("1.17"),
            gross_rent_multiplier=Decimal("11.46"),
            operating_expense_ratio=Decimal("0.1644"),
            break_even_occupancy=Decimal("0.8776"),
            rent_to_price_ratio=Decimal("0.0073"),
        ),
        maximum_offer=MaximumOfferResult(
            break_even_cash_flow_price=Decimal("430000"),
            target_monthly_cash_flow_price=None,
            target_cap_rate_price=None,
            target_cash_on_cash_price=None,
            target_dscr_price=None,
            binding_maximum_price=Decimal("430000"),
            asking_price_gap=Decimal("15000"),
            asking_price_satisfies_break_even=False,
            asking_price_satisfies_target_monthly_cash_flow=None,
            asking_price_satisfies_target_cap_rate=None,
            asking_price_satisfies_target_cash_on_cash=None,
            asking_price_satisfies_target_dscr=None,
        ),
        scenarios=[],
        stress_tests=[],
    )


def build_research_package(property_snapshot: VerifiedPropertySnapshot) -> ResearchPackage:
    return ResearchPackage(
        property=property_snapshot,
        metadata=ResearchPackageMetadata(
            total_duration_ms=123,
            completed_domains=["public_records"],
        ),
    )


def build_agent_research_package() -> UnifiedAgentResearchPackage:
    return UnifiedAgentResearchPackage(
        overall_data_confidence=Decimal("0.75"),
        execution_metadata=AgentExecutionMetadata(
            request_id="req-123",
            workflow_name="real_estate_agent_research",
            workflow_version="v1",
            prompt_version="v1",
            model_name="gpt-5-mini",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        ),
    )


def build_committee_output() -> InvestmentCommitteeOutput:
    return InvestmentCommitteeOutput(
        recommendation=InvestmentRecommendation.NEGOTIATE,
        recommendation_summary="Works only with a lower purchase price.",
        recommendation_confidence=Decimal("0.70"),
        asking_price=Decimal("445000"),
        investment_thesis="Stabilized rental with moderate leverage.",
        strongest_upside="Positive cash flow at the right basis.",
        strongest_downside="Thin margin at current pricing.",
    )
