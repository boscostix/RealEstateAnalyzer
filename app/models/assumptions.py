"""Input models for deterministic underwriting assumptions."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field

from app.models.verification import VerifiedPropertySnapshot


class FinancingType(StrEnum):
    CONVENTIONAL = "conventional"
    CASH = "cash"


class AnalysisPreset(StrEnum):
    CONSERVATIVE = "conservative"
    STANDARD = "standard"
    AGGRESSIVE = "aggressive"
    CUSTOM = "custom"


class AcquisitionAssumptions(BaseModel):
    closing_costs: Decimal | None = None
    closing_cost_percent: Decimal | None = None
    lender_fees: Decimal = Decimal("0")
    repairs: Decimal = Decimal("0")
    initial_reserves: Decimal = Decimal("0")
    other_acquisition_costs: Decimal = Decimal("0")


class FinancingAssumptions(BaseModel):
    type: FinancingType
    down_payment_amount: Decimal | None = None
    down_payment_percent: Decimal | None = None
    interest_rate_percent: Decimal | None = None
    loan_term_years: int | None = None
    loan_amount: Decimal | None = None
    points: Decimal = Decimal("0")
    additional_lender_fees: Decimal = Decimal("0")
    monthly_mortgage_insurance: Decimal = Decimal("0")


class IncomeAssumptions(BaseModel):
    monthly_rent: Decimal
    other_monthly_income: Decimal = Decimal("0")
    vacancy_percent: Decimal


class ExpenseAssumptions(BaseModel):
    annual_property_taxes: Decimal | None = None
    annual_insurance: Decimal
    annual_hoa: Decimal | None = None
    management_percent: Decimal = Decimal("0")
    maintenance_percent: Decimal | None = None
    maintenance_annual: Decimal | None = None
    capex_percent: Decimal | None = None
    capex_annual: Decimal | None = None
    leasing_fee_percent: Decimal = Decimal("0")
    tenant_turnover_frequency_years: Decimal = Decimal("1")
    turnover_cost: Decimal = Decimal("0")
    owner_paid_utilities_monthly: Decimal = Decimal("0")
    landscaping_monthly: Decimal = Decimal("0")
    pest_control_monthly: Decimal = Decimal("0")
    other_monthly_expenses: Decimal = Decimal("0")
    other_annual_expenses: Decimal = Decimal("0")


class ProjectionAssumptions(BaseModel):
    holding_period_years: int = 5
    annual_rent_growth_percent: Decimal = Decimal("2")
    annual_expense_growth_percent: Decimal = Decimal("2")
    annual_appreciation_percent: Decimal = Decimal("3")
    selling_cost_percent: Decimal = Decimal("6")


class TargetAssumptions(BaseModel):
    monthly_cash_flow: Decimal | None = None
    cap_rate_percent: Decimal | None = None
    cash_on_cash_percent: Decimal | None = None
    dscr: Decimal | None = None


class ScenarioOverrides(BaseModel):
    rent_percent_delta: Decimal = Decimal("0")
    vacancy_percent_delta: Decimal = Decimal("0")
    maintenance_percent_delta: Decimal = Decimal("0")
    capex_percent_delta: Decimal = Decimal("0")
    insurance_percent_delta: Decimal = Decimal("0")
    repairs_amount_delta: Decimal = Decimal("0")


class AnalysisAssumptions(BaseModel):
    purchase_price: Decimal
    preset: AnalysisPreset = AnalysisPreset.STANDARD
    financing: FinancingAssumptions
    acquisition: AcquisitionAssumptions
    income: IncomeAssumptions
    expenses: ExpenseAssumptions
    projections: ProjectionAssumptions = Field(default_factory=ProjectionAssumptions)
    targets: TargetAssumptions = Field(default_factory=TargetAssumptions)


class RunAnalysisRequest(BaseModel):
    property: VerifiedPropertySnapshot
    assumptions: AnalysisAssumptions
