"""Common helpers for deterministic Decimal-based calculations."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, getcontext

getcontext().prec = 28

MONEY_QUANT = Decimal("0.01")
RATIO_QUANT = Decimal("0.0001")


def to_decimal(value: Decimal | int | str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def ratio(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return value.quantize(RATIO_QUANT, rounding=ROUND_HALF_UP)


def percent_to_decimal(percent: Decimal) -> Decimal:
    return percent / Decimal("100")
