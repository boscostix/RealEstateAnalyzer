"""Maximum offer helper calculations."""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal


def binary_search_price(
    evaluator: Callable[[Decimal], bool],
    *,
    low: Decimal,
    high: Decimal,
    tolerance: Decimal = Decimal("1"),
    max_iterations: int = 100,
) -> Decimal | None:
    best: Decimal | None = None
    for _ in range(max_iterations):
        if high - low <= tolerance:
            break
        mid = (low + high) / Decimal("2")
        result = evaluator(mid)
        if result:
            best = mid
            low = mid
        else:
            high = mid
    return best
