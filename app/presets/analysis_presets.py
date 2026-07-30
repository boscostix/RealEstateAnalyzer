"""Named preset values for deterministic underwriting assumptions."""

from __future__ import annotations

from decimal import Decimal

from app.models.assumptions import AnalysisPreset

PRESET_VALUES: dict[AnalysisPreset, dict[str, Decimal]] = {
    AnalysisPreset.CONSERVATIVE: {
        "vacancy_percent": Decimal("7"),
        "management_percent": Decimal("10"),
        "maintenance_percent": Decimal("7"),
        "capex_percent": Decimal("7"),
        "annual_rent_growth_percent": Decimal("1"),
        "annual_expense_growth_percent": Decimal("3"),
        "annual_appreciation_percent": Decimal("2"),
        "selling_cost_percent": Decimal("7"),
    },
    AnalysisPreset.STANDARD: {
        "vacancy_percent": Decimal("5"),
        "management_percent": Decimal("8"),
        "maintenance_percent": Decimal("5"),
        "capex_percent": Decimal("5"),
        "annual_rent_growth_percent": Decimal("2"),
        "annual_expense_growth_percent": Decimal("2"),
        "annual_appreciation_percent": Decimal("3"),
        "selling_cost_percent": Decimal("6"),
    },
    AnalysisPreset.AGGRESSIVE: {
        "vacancy_percent": Decimal("3"),
        "management_percent": Decimal("0"),
        "maintenance_percent": Decimal("4"),
        "capex_percent": Decimal("4"),
        "annual_rent_growth_percent": Decimal("3"),
        "annual_expense_growth_percent": Decimal("2"),
        "annual_appreciation_percent": Decimal("4"),
        "selling_cost_percent": Decimal("5"),
    },
    AnalysisPreset.CUSTOM: {},
}


SCENARIO_ADJUSTMENTS: dict[str, dict[str, Decimal]] = {
    "conservative": {
        "rent_percent_delta": Decimal("-5"),
        "vacancy_percent_delta": Decimal("2"),
        "maintenance_percent_delta": Decimal("2"),
        "capex_percent_delta": Decimal("2"),
        "insurance_percent_delta": Decimal("10"),
        "repairs_amount_delta": Decimal("5000"),
    },
    "expected": {
        "rent_percent_delta": Decimal("0"),
        "vacancy_percent_delta": Decimal("0"),
        "maintenance_percent_delta": Decimal("0"),
        "capex_percent_delta": Decimal("0"),
        "insurance_percent_delta": Decimal("0"),
        "repairs_amount_delta": Decimal("0"),
    },
    "optimistic": {
        "rent_percent_delta": Decimal("5"),
        "vacancy_percent_delta": Decimal("-2"),
        "maintenance_percent_delta": Decimal("-1"),
        "capex_percent_delta": Decimal("-1"),
        "insurance_percent_delta": Decimal("-5"),
        "repairs_amount_delta": Decimal("-2500"),
    },
}
