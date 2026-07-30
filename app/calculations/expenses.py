"""Operating expense calculations."""

from __future__ import annotations

from decimal import Decimal

from app.calculations.common import money, percent_to_decimal


def monthly_from_annual(value: Decimal) -> Decimal:
    return money(value / Decimal("12"))


def annual_from_monthly(value: Decimal) -> Decimal:
    return money(value * Decimal("12"))


def percentage_expense(base_monthly_rent: Decimal, percent: Decimal) -> Decimal:
    return money(base_monthly_rent * percent_to_decimal(percent))


def leasing_turnover_monthly(
    monthly_rent: Decimal,
    leasing_fee_percent: Decimal,
    turnover_cost: Decimal,
    turnover_frequency_years: Decimal,
) -> Decimal:
    leasing_fee = monthly_rent * percent_to_decimal(leasing_fee_percent)
    annual_turnover = (
        Decimal("0")
        if turnover_frequency_years == 0
        else turnover_cost / turnover_frequency_years
    )
    return money((leasing_fee + annual_turnover) / Decimal("12"))
