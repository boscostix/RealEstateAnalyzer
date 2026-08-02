"""Income calculations."""

from __future__ import annotations

from decimal import Decimal

from app.calculations.common import money, percent_to_decimal


def vacancy_loss(monthly_gross_scheduled_income: Decimal, vacancy_percent: Decimal) -> Decimal:
    return money(monthly_gross_scheduled_income * percent_to_decimal(vacancy_percent))
