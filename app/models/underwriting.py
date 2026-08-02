"""Models for underwriting outputs."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.assumptions import AnalysisAssumptions, FinancingType
from app.models.verification import VerifiedPropertySnapshot


class AcquisitionResult(BaseModel):
    purchase_price: Decimal
    down_payment: Decimal
    base_loan_amount: Decimal
    financing_points: Decimal
    lender_fees: Decimal
    closing_costs: Decimal
    repairs: Decimal
    initial_reserves: Decimal
    other_acquisition_costs: Decimal
    total_cash_required_at_closing: Decimal
    total_project_cost: Decimal


class FinancingResult(BaseModel):
    financing_type: FinancingType
    original_loan_balance: Decimal
    monthly_principal_interest: Decimal
    annual_debt_service: Decimal
    monthly_mortgage_insurance: Decimal
    total_monthly_debt_payment: Decimal


class IncomeResult(BaseModel):
    monthly_scheduled_rent: Decimal
    monthly_other_income: Decimal
    monthly_gross_scheduled_income: Decimal
    monthly_vacancy_loss: Decimal
    monthly_effective_gross_income: Decimal
    annual_gross_scheduled_income: Decimal
    annual_vacancy_loss: Decimal
    annual_effective_gross_income: Decimal


class ExpenseLineItem(BaseModel):
    monthly: Decimal
    annual: Decimal


class OperatingExpenseResult(BaseModel):
    property_taxes: ExpenseLineItem
    insurance: ExpenseLineItem
    hoa: ExpenseLineItem
    management: ExpenseLineItem
    maintenance: ExpenseLineItem
    capital_expenditures: ExpenseLineItem
    leasing_turnover: ExpenseLineItem
    utilities: ExpenseLineItem
    landscaping: ExpenseLineItem
    pest_control: ExpenseLineItem
    other: ExpenseLineItem
    total_monthly_operating_expenses: Decimal
    total_annual_operating_expenses: Decimal


class InvestmentMetrics(BaseModel):
    noi: Decimal
    monthly_pre_tax_cash_flow: Decimal
    annual_pre_tax_cash_flow: Decimal
    cap_rate: Decimal | None
    cash_on_cash_return: Decimal | None
    dscr: Decimal | None
    gross_rent_multiplier: Decimal | None
    operating_expense_ratio: Decimal | None
    break_even_occupancy: Decimal | None
    rent_to_price_ratio: Decimal | None


class MaximumOfferResult(BaseModel):
    break_even_cash_flow_price: Decimal | None
    target_monthly_cash_flow_price: Decimal | None
    target_cap_rate_price: Decimal | None
    target_cash_on_cash_price: Decimal | None
    target_dscr_price: Decimal | None
    binding_maximum_price: Decimal | None
    asking_price_gap: Decimal | None
    asking_price_satisfies_break_even: bool | None
    asking_price_satisfies_target_monthly_cash_flow: bool | None
    asking_price_satisfies_target_cap_rate: bool | None
    asking_price_satisfies_target_cash_on_cash: bool | None
    asking_price_satisfies_target_dscr: bool | None
    warnings: list[str] = Field(default_factory=list)


class ScenarioResult(BaseModel):
    name: str
    base_assumptions: AnalysisAssumptions
    adjustments: dict[str, Decimal]
    final_assumptions_used: AnalysisAssumptions
    acquisition: AcquisitionResult
    financing: FinancingResult
    income: IncomeResult
    operating_expenses: OperatingExpenseResult
    metrics: InvestmentMetrics
    warnings: list[str] = Field(default_factory=list)


class StressTestResult(BaseModel):
    identifier: str
    description: str
    changed_assumptions: dict[str, Decimal | str]
    change_in_monthly_cash_flow: Decimal
    change_in_annual_cash_flow: Decimal
    change_in_cash_on_cash_return: Decimal | None
    cash_flow_remains_positive: bool
    additional_cash_required: Decimal
    stressed_metrics: InvestmentMetrics
    warnings: list[str] = Field(default_factory=list)


class UnderwritingAnalysis(BaseModel):
    property: VerifiedPropertySnapshot
    assumptions_used: AnalysisAssumptions
    acquisition: AcquisitionResult
    financing: FinancingResult
    income: IncomeResult
    operating_expenses: OperatingExpenseResult
    metrics: InvestmentMetrics
    maximum_offer: MaximumOfferResult
    scenarios: list[ScenarioResult]
    stress_tests: list[StressTestResult]
    warnings: list[str] = Field(default_factory=list)


class AnalysisMetadata(BaseModel):
    calculation_version: str = "v1"
    calculated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RunAnalysisResponse(BaseModel):
    success: bool
    analysis: UnderwritingAnalysis | None = None
    metadata: AnalysisMetadata | None = None
