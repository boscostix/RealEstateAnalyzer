"""Investment return metrics."""

from __future__ import annotations

from decimal import Decimal


def safe_divide(numerator: Decimal, denominator: Decimal) -> Decimal | None:
    if denominator == 0:
        return None
    return numerator / denominator
