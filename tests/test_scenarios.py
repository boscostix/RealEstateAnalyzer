"""Tests for underwriting scenarios."""

from __future__ import annotations

from decimal import Decimal

from app.models.assumptions import (
    AcquisitionAssumptions,
    AnalysisAssumptions,
    ExpenseAssumptions,
    FinancingAssumptions,
    FinancingType,
    IncomeAssumptions,
)
from app.models.verification import VerificationStatus, VerifiedField, VerifiedPropertySnapshot
from app.services.underwriting_service import UnderwritingService


def build_property() -> VerifiedPropertySnapshot:
    return VerifiedPropertySnapshot(
        source_url="https://www.zillow.com/example",
        provider="zillow",
        full_address=VerifiedField[str](
            extracted_value="123 Main St",
            final_value="123 Main St",
            status=VerificationStatus.VERIFIED,
        ),
        asking_price=VerifiedField[Decimal](
            extracted_value=Decimal("300000"),
            final_value=Decimal("300000"),
            status=VerificationStatus.VERIFIED,
        ),
        annual_property_tax=VerifiedField[Decimal](
            extracted_value=Decimal("3600"),
            final_value=Decimal("3600"),
            status=VerificationStatus.VERIFIED,
        ),
        annual_hoa=VerifiedField[Decimal](
            extracted_value=Decimal("0"),
            final_value=Decimal("0"),
            status=VerificationStatus.CORRECTED,
        ),
        property_type=VerifiedField[str](
            extracted_value="single_family",
            final_value="single_family",
            status=VerificationStatus.VERIFIED,
        ),
    )


def build_assumptions() -> AnalysisAssumptions:
    return AnalysisAssumptions(
        purchase_price=Decimal("280000"),
        financing=FinancingAssumptions(
            type=FinancingType.CONVENTIONAL,
            down_payment_percent=Decimal("20"),
            interest_rate_percent=Decimal("6.5"),
            loan_term_years=30,
        ),
        acquisition=AcquisitionAssumptions(
            closing_cost_percent=Decimal("3"),
            repairs=Decimal("5000"),
            initial_reserves=Decimal("3000"),
        ),
        income=IncomeAssumptions(
            monthly_rent=Decimal("2500"),
            other_monthly_income=Decimal("0"),
            vacancy_percent=Decimal("5"),
        ),
        expenses=ExpenseAssumptions(
            annual_insurance=Decimal("1800"),
            annual_property_taxes=Decimal("3600"),
            annual_hoa=Decimal("0"),
            management_percent=Decimal("8"),
            maintenance_percent=Decimal("5"),
            capex_percent=Decimal("5"),
        ),
    )


def test_scenarios_include_three_named_variants() -> None:
    service = UnderwritingService()
    scenarios = service._scenarios(build_property(), build_assumptions())
    names = [scenario.name for scenario in scenarios]
    assert names == ["conservative", "expected", "optimistic"]

