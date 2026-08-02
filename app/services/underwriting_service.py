"""Deterministic underwriting orchestration."""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal

from app.calculations.acquisition import resolve_amount_or_percent
from app.calculations.common import money, percent_to_decimal, ratio
from app.calculations.expenses import (
    annual_from_monthly,
    leasing_turnover_monthly,
    monthly_from_annual,
    percentage_expense,
)
from app.calculations.income import vacancy_loss
from app.calculations.maximum_offer import binary_search_price
from app.calculations.mortgage import calculate_monthly_payment
from app.calculations.returns import safe_divide
from app.exceptions import (
    InvalidAssumptionError,
    MissingAnalysisInputError,
    UnsupportedFinancingTypeError,
)
from app.models.assumptions import (
    AnalysisAssumptions,
    AnalysisPreset,
    FinancingType,
    RunAnalysisRequest,
)
from app.models.underwriting import (
    AcquisitionResult,
    AnalysisMetadata,
    ExpenseLineItem,
    FinancingResult,
    IncomeResult,
    InvestmentMetrics,
    MaximumOfferResult,
    OperatingExpenseResult,
    RunAnalysisResponse,
    ScenarioResult,
    StressTestResult,
    UnderwritingAnalysis,
)
from app.models.verification import VerificationStatus, VerifiedPropertySnapshot
from app.presets.analysis_presets import PRESET_VALUES, SCENARIO_ADJUSTMENTS


class UnderwritingService:
    """Main deterministic underwriting service."""

    def run(self, request: RunAnalysisRequest) -> RunAnalysisResponse:
        property_snapshot = request.property
        assumptions = self._apply_preset(request.assumptions)
        warnings = self._validate(property_snapshot, assumptions)

        acquisition = self._acquisition(property_snapshot, assumptions)
        financing = self._financing(assumptions, acquisition)
        income = self._income(assumptions)
        expenses = self._expenses(property_snapshot, assumptions, income)
        metrics = self._metrics(acquisition, financing, income, expenses)
        warnings.extend(self._warning_rules(property_snapshot, assumptions, metrics))
        maximum_offer = self._maximum_offer(property_snapshot, assumptions)
        scenarios = self._scenarios(property_snapshot, assumptions)
        stress_tests = self._stress_tests(property_snapshot, assumptions, metrics)

        analysis = UnderwritingAnalysis(
            property=property_snapshot,
            assumptions_used=assumptions,
            acquisition=acquisition,
            financing=financing,
            income=income,
            operating_expenses=expenses,
            metrics=metrics,
            maximum_offer=maximum_offer,
            scenarios=scenarios,
            stress_tests=stress_tests,
            warnings=warnings,
        )
        return RunAnalysisResponse(
            success=True,
            analysis=analysis,
            metadata=AnalysisMetadata(),
        )

    def _apply_preset(self, assumptions: AnalysisAssumptions) -> AnalysisAssumptions:
        if assumptions.preset == AnalysisPreset.CUSTOM:
            return assumptions
        updated = assumptions.model_copy(deep=True)
        preset = PRESET_VALUES[assumptions.preset]
        if updated.income.vacancy_percent is None:
            updated.income.vacancy_percent = preset["vacancy_percent"]
        if updated.expenses.management_percent == Decimal("0"):
            updated.expenses.management_percent = preset["management_percent"]
        if updated.expenses.maintenance_percent is None:
            updated.expenses.maintenance_percent = preset["maintenance_percent"]
        if updated.expenses.capex_percent is None:
            updated.expenses.capex_percent = preset["capex_percent"]
        updated.projections.annual_rent_growth_percent = preset["annual_rent_growth_percent"]
        updated.projections.annual_expense_growth_percent = preset["annual_expense_growth_percent"]
        updated.projections.annual_appreciation_percent = preset["annual_appreciation_percent"]
        updated.projections.selling_cost_percent = preset["selling_cost_percent"]
        return updated

    def _validate(
        self,
        property_snapshot: VerifiedPropertySnapshot,
        assumptions: AnalysisAssumptions,
    ) -> list[str]:
        missing_fields: list[str] = []
        if assumptions.purchase_price <= 0:
            raise MissingAnalysisInputError(message="Purchase price is required.")
        if assumptions.income.monthly_rent < 0:
            raise InvalidAssumptionError(message="Monthly rent cannot be negative.")
        if assumptions.expenses.annual_insurance < 0:
            raise InvalidAssumptionError(message="Annual insurance cannot be negative.")
        if (
            assumptions.expenses.annual_hoa is None
            and property_snapshot.annual_hoa.final_value is None
        ):
            missing_fields.append("annual_hoa")
        if (
            assumptions.expenses.annual_property_taxes is None
            and property_snapshot.annual_property_tax.final_value is None
        ):
            missing_fields.append("annual_property_taxes")
        if missing_fields:
            raise MissingAnalysisInputError(
                message=f"Missing required analysis inputs: {', '.join(missing_fields)}."
            )
        financing = assumptions.financing
        if financing.type == FinancingType.CONVENTIONAL:
            if financing.interest_rate_percent is None or financing.loan_term_years is None:
                raise MissingAnalysisInputError(
                    message="Interest rate and loan term are required for financed purchases."
                )
            if financing.interest_rate_percent < 0:
                raise InvalidAssumptionError(message="Interest rate cannot be negative.")
            if financing.loan_term_years <= 0:
                raise InvalidAssumptionError(message="Loan term must be positive.")
        elif financing.type != FinancingType.CASH:
            raise UnsupportedFinancingTypeError()
        return []

    def _down_payment(self, assumptions: AnalysisAssumptions) -> Decimal:
        financing = assumptions.financing
        price = assumptions.purchase_price
        if financing.type == FinancingType.CASH:
            return money(price)
        if financing.loan_amount is not None and financing.down_payment_amount is not None:
            raise InvalidAssumptionError(
                message="Provide either down payment amount or loan amount, not both."
            )
        if financing.down_payment_amount is not None:
            return money(financing.down_payment_amount)
        if financing.down_payment_percent is not None:
            return money(price * percent_to_decimal(financing.down_payment_percent))
        if financing.loan_amount is not None:
            return money(price - financing.loan_amount)
        raise MissingAnalysisInputError(
            message="Down payment or loan amount is required for financed purchases."
        )

    def _acquisition(
        self,
        property_snapshot: VerifiedPropertySnapshot,
        assumptions: AnalysisAssumptions,
    ) -> AcquisitionResult:
        purchase_price = money(assumptions.purchase_price)
        down_payment = self._down_payment(assumptions)
        if down_payment > purchase_price:
            raise InvalidAssumptionError(
                message="The down payment cannot exceed the purchase price."
            )
        if assumptions.financing.type == FinancingType.CASH:
            loan_amount = Decimal("0")
        else:
            base_loan_amount = (
                assumptions.financing.loan_amount
                if assumptions.financing.loan_amount is not None
                else purchase_price - down_payment
            )
            loan_amount = money(base_loan_amount)
        closing_costs = resolve_amount_or_percent(
            purchase_price,
            assumptions.acquisition.closing_costs,
            assumptions.acquisition.closing_cost_percent,
        )
        financing_points = money(loan_amount * percent_to_decimal(assumptions.financing.points))
        lender_fees = money(
            assumptions.acquisition.lender_fees + assumptions.financing.additional_lender_fees
        )
        repairs = money(assumptions.acquisition.repairs)
        reserves = money(assumptions.acquisition.initial_reserves)
        other_costs = money(assumptions.acquisition.other_acquisition_costs)
        total_cash = money(
            down_payment
            + closing_costs
            + financing_points
            + lender_fees
            + repairs
            + reserves
            + other_costs
        )
        total_project_cost = money(purchase_price + closing_costs + repairs + other_costs)
        return AcquisitionResult(
            purchase_price=purchase_price,
            down_payment=down_payment,
            base_loan_amount=loan_amount,
            financing_points=financing_points,
            lender_fees=lender_fees,
            closing_costs=closing_costs,
            repairs=repairs,
            initial_reserves=reserves,
            other_acquisition_costs=other_costs,
            total_cash_required_at_closing=total_cash,
            total_project_cost=total_project_cost,
        )

    def _financing(
        self,
        assumptions: AnalysisAssumptions,
        acquisition: AcquisitionResult,
    ) -> FinancingResult:
        if assumptions.financing.type == FinancingType.CASH:
            return FinancingResult(
                financing_type=FinancingType.CASH,
                original_loan_balance=Decimal("0.00"),
                monthly_principal_interest=Decimal("0.00"),
                annual_debt_service=Decimal("0.00"),
                monthly_mortgage_insurance=Decimal("0.00"),
                total_monthly_debt_payment=Decimal("0.00"),
            )
        monthly_pi = calculate_monthly_payment(
            acquisition.base_loan_amount,
            assumptions.financing.interest_rate_percent or Decimal("0"),
            assumptions.financing.loan_term_years or 30,
        )
        monthly_mi = money(assumptions.financing.monthly_mortgage_insurance)
        total_monthly = money(monthly_pi + monthly_mi)
        return FinancingResult(
            financing_type=assumptions.financing.type,
            original_loan_balance=acquisition.base_loan_amount,
            monthly_principal_interest=monthly_pi,
            annual_debt_service=money(total_monthly * Decimal("12")),
            monthly_mortgage_insurance=monthly_mi,
            total_monthly_debt_payment=total_monthly,
        )

    def _income(self, assumptions: AnalysisAssumptions) -> IncomeResult:
        monthly_rent = money(assumptions.income.monthly_rent)
        monthly_other = money(assumptions.income.other_monthly_income)
        monthly_gsi = money(monthly_rent + monthly_other)
        monthly_vacancy = vacancy_loss(monthly_gsi, assumptions.income.vacancy_percent)
        monthly_egi = money(monthly_gsi - monthly_vacancy)
        annual_gsi = money(monthly_gsi * Decimal("12"))
        annual_vacancy = money(monthly_vacancy * Decimal("12"))
        annual_egi = money(monthly_egi * Decimal("12"))
        return IncomeResult(
            monthly_scheduled_rent=monthly_rent,
            monthly_other_income=monthly_other,
            monthly_gross_scheduled_income=monthly_gsi,
            monthly_vacancy_loss=monthly_vacancy,
            monthly_effective_gross_income=monthly_egi,
            annual_gross_scheduled_income=annual_gsi,
            annual_vacancy_loss=annual_vacancy,
            annual_effective_gross_income=annual_egi,
        )

    def _expenses(
        self,
        property_snapshot: VerifiedPropertySnapshot,
        assumptions: AnalysisAssumptions,
        income: IncomeResult,
    ) -> OperatingExpenseResult:
        annual_taxes = money(
            assumptions.expenses.annual_property_taxes
            if assumptions.expenses.annual_property_taxes is not None
            else property_snapshot.annual_property_tax.final_value or Decimal("0")
        )
        annual_hoa = money(
            assumptions.expenses.annual_hoa
            if assumptions.expenses.annual_hoa is not None
            else property_snapshot.annual_hoa.final_value or Decimal("0")
        )
        tax_item = ExpenseLineItem(
            monthly=monthly_from_annual(annual_taxes),
            annual=annual_taxes,
        )
        insurance_item = ExpenseLineItem(
            monthly=monthly_from_annual(money(assumptions.expenses.annual_insurance)),
            annual=money(assumptions.expenses.annual_insurance),
        )
        hoa_item = ExpenseLineItem(monthly=monthly_from_annual(annual_hoa), annual=annual_hoa)
        management_monthly = percentage_expense(
            income.monthly_scheduled_rent,
            assumptions.expenses.management_percent,
        )
        management_item = ExpenseLineItem(
            monthly=management_monthly,
            annual=annual_from_monthly(management_monthly),
        )
        maintenance_monthly = (
            percentage_expense(
                income.monthly_scheduled_rent,
                assumptions.expenses.maintenance_percent,
            )
            if assumptions.expenses.maintenance_percent is not None
            else monthly_from_annual(money(assumptions.expenses.maintenance_annual or Decimal("0")))
        )
        maintenance_item = ExpenseLineItem(
            monthly=maintenance_monthly,
            annual=annual_from_monthly(maintenance_monthly),
        )
        capex_monthly = (
            percentage_expense(
                income.monthly_scheduled_rent,
                assumptions.expenses.capex_percent,
            )
            if assumptions.expenses.capex_percent is not None
            else monthly_from_annual(money(assumptions.expenses.capex_annual or Decimal("0")))
        )
        capex_item = ExpenseLineItem(
            monthly=capex_monthly,
            annual=annual_from_monthly(capex_monthly),
        )
        leasing_monthly = leasing_turnover_monthly(
            income.monthly_scheduled_rent,
            assumptions.expenses.leasing_fee_percent,
            money(assumptions.expenses.turnover_cost),
            assumptions.expenses.tenant_turnover_frequency_years,
        )
        leasing_item = ExpenseLineItem(
            monthly=leasing_monthly,
            annual=annual_from_monthly(leasing_monthly),
        )
        utility_item = ExpenseLineItem(
            monthly=money(assumptions.expenses.owner_paid_utilities_monthly),
            annual=annual_from_monthly(money(assumptions.expenses.owner_paid_utilities_monthly)),
        )
        landscape_item = ExpenseLineItem(
            monthly=money(assumptions.expenses.landscaping_monthly),
            annual=annual_from_monthly(money(assumptions.expenses.landscaping_monthly)),
        )
        pest_item = ExpenseLineItem(
            monthly=money(assumptions.expenses.pest_control_monthly),
            annual=annual_from_monthly(money(assumptions.expenses.pest_control_monthly)),
        )
        other_monthly = money(assumptions.expenses.other_monthly_expenses) + monthly_from_annual(
            money(assumptions.expenses.other_annual_expenses)
        )
        other_item = ExpenseLineItem(
            monthly=money(other_monthly),
            annual=annual_from_monthly(money(other_monthly)),
        )
        total_monthly = money(
            tax_item.monthly
            + insurance_item.monthly
            + hoa_item.monthly
            + management_item.monthly
            + maintenance_item.monthly
            + capex_item.monthly
            + leasing_item.monthly
            + utility_item.monthly
            + landscape_item.monthly
            + pest_item.monthly
            + other_item.monthly
        )
        return OperatingExpenseResult(
            property_taxes=tax_item,
            insurance=insurance_item,
            hoa=hoa_item,
            management=management_item,
            maintenance=maintenance_item,
            capital_expenditures=capex_item,
            leasing_turnover=leasing_item,
            utilities=utility_item,
            landscaping=landscape_item,
            pest_control=pest_item,
            other=other_item,
            total_monthly_operating_expenses=total_monthly,
            total_annual_operating_expenses=annual_from_monthly(total_monthly),
        )

    def _metrics(
        self,
        acquisition: AcquisitionResult,
        financing: FinancingResult,
        income: IncomeResult,
        expenses: OperatingExpenseResult,
    ) -> InvestmentMetrics:
        noi = money(income.annual_effective_gross_income - expenses.total_annual_operating_expenses)
        monthly_cash_flow = money(
            income.monthly_effective_gross_income
            - expenses.total_monthly_operating_expenses
            - financing.total_monthly_debt_payment
        )
        annual_cash_flow = annual_from_monthly(monthly_cash_flow)
        cap_rate = ratio(safe_divide(noi, acquisition.purchase_price))
        coc = ratio(safe_divide(annual_cash_flow, acquisition.total_cash_required_at_closing))
        dscr = (
            None
            if financing.annual_debt_service == 0
            else ratio(safe_divide(noi, financing.annual_debt_service))
        )
        grm = ratio(safe_divide(acquisition.purchase_price, income.annual_gross_scheduled_income))
        oer = ratio(
            safe_divide(
                expenses.total_annual_operating_expenses,
                income.annual_effective_gross_income,
            )
        )
        break_even = ratio(
            safe_divide(
                expenses.total_annual_operating_expenses + financing.annual_debt_service,
                income.annual_gross_scheduled_income,
            )
        )
        rent_to_price = ratio(
            safe_divide(income.monthly_scheduled_rent, acquisition.purchase_price)
        )
        return InvestmentMetrics(
            noi=noi,
            monthly_pre_tax_cash_flow=monthly_cash_flow,
            annual_pre_tax_cash_flow=annual_cash_flow,
            cap_rate=cap_rate,
            cash_on_cash_return=coc,
            dscr=dscr,
            gross_rent_multiplier=grm,
            operating_expense_ratio=oer,
            break_even_occupancy=break_even,
            rent_to_price_ratio=rent_to_price,
        )

    def _maximum_offer(
        self,
        property_snapshot: VerifiedPropertySnapshot,
        assumptions: AnalysisAssumptions,
    ) -> MaximumOfferResult:
        asking = property_snapshot.asking_price.final_value or assumptions.purchase_price
        warnings: list[str] = []

        def evaluate(
            price: Decimal,
            predicate: Callable[[InvestmentMetrics], bool],
        ) -> bool:
            local = assumptions.model_copy(deep=True)
            local.purchase_price = money(price)
            acquisition = self._acquisition(property_snapshot, local)
            financing = self._financing(local, acquisition)
            income = self._income(local)
            expenses = self._expenses(property_snapshot, local, income)
            metrics = self._metrics(acquisition, financing, income, expenses)
            return predicate(metrics)

        def solve(predicate: Callable[[InvestmentMetrics], bool]) -> Decimal | None:
            return binary_search_price(
                lambda price: evaluate(price, predicate),
                low=Decimal("1"),
                high=max(asking * Decimal("2"), Decimal("100000")),
            )

        break_even = solve(lambda metrics: metrics.monthly_pre_tax_cash_flow >= 0)
        target_cf = (
            solve(
                lambda metrics: (
                    assumptions.targets.monthly_cash_flow is not None
                    and metrics.monthly_pre_tax_cash_flow >= assumptions.targets.monthly_cash_flow
                )
            )
            if assumptions.targets.monthly_cash_flow is not None
            else None
        )
        target_cap = (
            solve(
                lambda metrics: (
                    metrics.cap_rate is not None
                    and metrics.cap_rate
                    >= percent_to_decimal(assumptions.targets.cap_rate_percent or Decimal("0"))
                )
            )
            if assumptions.targets.cap_rate_percent is not None
            else None
        )
        target_coc = (
            solve(
                lambda metrics: (
                    metrics.cash_on_cash_return is not None
                    and metrics.cash_on_cash_return
                    >= percent_to_decimal(assumptions.targets.cash_on_cash_percent or Decimal("0"))
                )
            )
            if assumptions.targets.cash_on_cash_percent is not None
            else None
        )
        target_dscr = (
            solve(
                lambda metrics: (
                    metrics.dscr is not None
                    and metrics.dscr >= (assumptions.targets.dscr or Decimal("0"))
                )
            )
            if assumptions.targets.dscr is not None
            else None
        )
        available = [
            item
            for item in [
                break_even,
                target_cf,
                target_cap,
                target_coc,
                target_dscr,
            ]
            if item is not None
        ]
        binding = min(available) if available else None
        return MaximumOfferResult(
            break_even_cash_flow_price=money(break_even) if break_even is not None else None,
            target_monthly_cash_flow_price=money(target_cf) if target_cf is not None else None,
            target_cap_rate_price=money(target_cap) if target_cap is not None else None,
            target_cash_on_cash_price=money(target_coc) if target_coc is not None else None,
            target_dscr_price=money(target_dscr) if target_dscr is not None else None,
            binding_maximum_price=money(binding) if binding is not None else None,
            asking_price_gap=None if binding is None else money(asking - binding),
            asking_price_satisfies_break_even=(
                None if break_even is None else asking <= break_even
            ),
            asking_price_satisfies_target_monthly_cash_flow=(
                None if target_cf is None else asking <= target_cf
            ),
            asking_price_satisfies_target_cap_rate=(
                None if target_cap is None else asking <= target_cap
            ),
            asking_price_satisfies_target_cash_on_cash=(
                None if target_coc is None else asking <= target_coc
            ),
            asking_price_satisfies_target_dscr=(
                None if target_dscr is None else asking <= target_dscr
            ),
            warnings=warnings,
        )

    def _scenarios(
        self,
        property_snapshot: VerifiedPropertySnapshot,
        assumptions: AnalysisAssumptions,
    ) -> list[ScenarioResult]:
        scenarios: list[ScenarioResult] = []
        for name, adjustments in SCENARIO_ADJUSTMENTS.items():
            scenario_assumptions = assumptions.model_copy(deep=True)
            scenario_assumptions.income.monthly_rent = money(
                assumptions.income.monthly_rent
                * (Decimal("1") + percent_to_decimal(adjustments["rent_percent_delta"]))
            )
            scenario_assumptions.income.vacancy_percent = (
                assumptions.income.vacancy_percent + adjustments["vacancy_percent_delta"]
            )
            if scenario_assumptions.expenses.maintenance_percent is not None:
                scenario_assumptions.expenses.maintenance_percent += adjustments[
                    "maintenance_percent_delta"
                ]
            if scenario_assumptions.expenses.capex_percent is not None:
                scenario_assumptions.expenses.capex_percent += adjustments["capex_percent_delta"]
            scenario_assumptions.expenses.annual_insurance = money(
                assumptions.expenses.annual_insurance
                * (Decimal("1") + percent_to_decimal(adjustments["insurance_percent_delta"]))
            )
            scenario_assumptions.acquisition.repairs = money(
                assumptions.acquisition.repairs + adjustments["repairs_amount_delta"]
            )
            acquisition = self._acquisition(property_snapshot, scenario_assumptions)
            financing = self._financing(scenario_assumptions, acquisition)
            income = self._income(scenario_assumptions)
            expenses = self._expenses(property_snapshot, scenario_assumptions, income)
            metrics = self._metrics(acquisition, financing, income, expenses)
            scenarios.append(
                ScenarioResult(
                    name=name,
                    base_assumptions=assumptions,
                    adjustments=adjustments,
                    final_assumptions_used=scenario_assumptions,
                    acquisition=acquisition,
                    financing=financing,
                    income=income,
                    operating_expenses=expenses,
                    metrics=metrics,
                    warnings=[],
                )
            )
        return scenarios

    def _stress_tests(
        self,
        property_snapshot: VerifiedPropertySnapshot,
        assumptions: AnalysisAssumptions,
        base_metrics: InvestmentMetrics,
    ) -> list[StressTestResult]:
        definitions = [
            ("rent_down_5", "Rent decreases by 5%.", {"rent_delta": Decimal("-5")}),
            ("rent_down_10", "Rent decreases by 10%.", {"rent_delta": Decimal("-10")}),
            ("vacancy_double", "Vacancy doubles.", {"vacancy_multiplier": Decimal("2")}),
            ("tax_up_10", "Property taxes increase by 10%.", {"tax_delta": Decimal("10")}),
            ("tax_up_20", "Property taxes increase by 20%.", {"tax_delta": Decimal("20")}),
            (
                "insurance_up_25",
                "Insurance increases by 25%.",
                {"insurance_delta": Decimal("25")},
            ),
            (
                "repair_5000",
                "A $5,000 immediate repair occurs.",
                {"repair_delta": Decimal("5000")},
            ),
            (
                "repair_15000",
                "A $15,000 immediate repair occurs.",
                {"repair_delta": Decimal("15000")},
            ),
            (
                "repair_30000",
                "A $30,000 immediate repair occurs.",
                {"repair_delta": Decimal("30000")},
            ),
            (
                "management_required",
                "Property management becomes necessary.",
                {"management_percent": Decimal("8")},
            ),
            ("rent_growth_zero", "Rent growth becomes zero.", {"rent_growth": Decimal("0")}),
            (
                "appreciation_zero",
                "Property appreciation becomes zero.",
                {"appreciation": Decimal("0")},
            ),
        ]
        base_acquisition = self._acquisition(property_snapshot, assumptions)
        results: list[StressTestResult] = []
        for identifier, description, change in definitions:
            stressed = assumptions.model_copy(deep=True)
            if "rent_delta" in change:
                stressed.income.monthly_rent = money(
                    stressed.income.monthly_rent
                    * (Decimal("1") + percent_to_decimal(change["rent_delta"]))
                )
            if "vacancy_multiplier" in change:
                stressed.income.vacancy_percent = (
                    stressed.income.vacancy_percent * change["vacancy_multiplier"]
                )
            if "tax_delta" in change:
                base_taxes = (
                    stressed.expenses.annual_property_taxes
                    or property_snapshot.annual_property_tax.final_value
                    or Decimal("0")
                )
                stressed.expenses.annual_property_taxes = money(
                    base_taxes * (Decimal("1") + percent_to_decimal(change["tax_delta"]))
                )
            if "insurance_delta" in change:
                stressed.expenses.annual_insurance = money(
                    stressed.expenses.annual_insurance
                    * (Decimal("1") + percent_to_decimal(change["insurance_delta"]))
                )
            if "repair_delta" in change:
                stressed.acquisition.repairs = money(
                    stressed.acquisition.repairs + change["repair_delta"]
                )
            if "management_percent" in change:
                stressed.expenses.management_percent = change["management_percent"]
            if "rent_growth" in change:
                stressed.projections.annual_rent_growth_percent = change["rent_growth"]
            if "appreciation" in change:
                stressed.projections.annual_appreciation_percent = change["appreciation"]
            acquisition = self._acquisition(property_snapshot, stressed)
            financing = self._financing(stressed, acquisition)
            income = self._income(stressed)
            expenses = self._expenses(property_snapshot, stressed, income)
            metrics = self._metrics(acquisition, financing, income, expenses)
            results.append(
                StressTestResult(
                    identifier=identifier,
                    description=description,
                    changed_assumptions={k: str(v) for k, v in change.items()},
                    change_in_monthly_cash_flow=money(
                        metrics.monthly_pre_tax_cash_flow - base_metrics.monthly_pre_tax_cash_flow
                    ),
                    change_in_annual_cash_flow=money(
                        metrics.annual_pre_tax_cash_flow - base_metrics.annual_pre_tax_cash_flow
                    ),
                    change_in_cash_on_cash_return=None
                    if (
                        metrics.cash_on_cash_return is None
                        or base_metrics.cash_on_cash_return is None
                    )
                    else ratio(metrics.cash_on_cash_return - base_metrics.cash_on_cash_return),
                    cash_flow_remains_positive=metrics.monthly_pre_tax_cash_flow >= 0,
                    additional_cash_required=money(
                        acquisition.total_cash_required_at_closing
                        - base_acquisition.total_cash_required_at_closing
                    ),
                    stressed_metrics=metrics,
                    warnings=[],
                )
            )
        return results

    def _warning_rules(
        self,
        property_snapshot: VerifiedPropertySnapshot,
        assumptions: AnalysisAssumptions,
        metrics: InvestmentMetrics,
    ) -> list[str]:
        warnings: list[str] = []
        if (
            assumptions.expenses.maintenance_percent == 0
            or assumptions.expenses.maintenance_annual == 0
        ):
            warnings.append("zero_maintenance_reserve")
        if assumptions.expenses.capex_percent == 0 or assumptions.expenses.capex_annual == 0:
            warnings.append("zero_capex_reserve")
        if assumptions.income.vacancy_percent == 0:
            warnings.append("zero_vacancy")
        if assumptions.expenses.annual_insurance < Decimal("500"):
            warnings.append("insurance_unusually_low")
        if (
            assumptions.expenses.annual_property_taxes
            or property_snapshot.annual_property_tax.final_value
            or Decimal("0")
        ) == 0:
            warnings.append("property_taxes_zero")
        if assumptions.income.monthly_rent == 0:
            warnings.append("expected_rent_zero")
        if metrics.monthly_pre_tax_cash_flow < 0:
            warnings.append("negative_monthly_cash_flow")
        if metrics.dscr is not None and metrics.dscr < Decimal("1.0"):
            warnings.append("dscr_below_one")
        if metrics.cash_on_cash_return is None:
            warnings.append("cash_on_cash_not_calculable")
        if (
            property_snapshot.asking_price.final_value is not None
            and assumptions.purchase_price != property_snapshot.asking_price.final_value
        ):
            warnings.append("purchase_price_differs_from_asking_price")
        for field_name in [
            "asking_price",
            "annual_property_tax",
            "annual_hoa",
            "property_type",
        ]:
            field = getattr(property_snapshot, field_name)
            if field.status == VerificationStatus.UNVERIFIED:
                warnings.append(f"unverified_field_used:{field_name}")
            if field.status == VerificationStatus.ESTIMATED:
                warnings.append(f"estimated_field_used:{field_name}")
        return warnings
