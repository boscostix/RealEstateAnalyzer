"""Mortgage and amortization calculations."""

from __future__ import annotations

from decimal import Decimal

from app.calculations.common import money, percent_to_decimal


def calculate_monthly_payment(
    principal: Decimal,
    annual_interest_rate_percent: Decimal,
    loan_term_years: int,
) -> Decimal:
    if principal <= 0:
        return Decimal("0.00")
    total_payments = loan_term_years * 12
    if annual_interest_rate_percent == 0:
        return money(principal / Decimal(total_payments))
    monthly_rate = percent_to_decimal(annual_interest_rate_percent) / Decimal("12")
    numerator = principal * monthly_rate
    denominator = Decimal("1") - (Decimal("1") + monthly_rate) ** Decimal(-total_payments)
    return money(numerator / denominator)

