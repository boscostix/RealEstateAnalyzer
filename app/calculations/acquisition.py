"""Acquisition cost calculations."""

from __future__ import annotations

from decimal import Decimal

from app.calculations.common import money, percent_to_decimal


def resolve_amount_or_percent(
    base_amount: Decimal,
    fixed_amount: Decimal | None,
    percent: Decimal | None,
) -> Decimal:
    if fixed_amount is not None:
        return money(fixed_amount)
    if percent is not None:
        return money(base_amount * percent_to_decimal(percent))
    return Decimal("0.00")
