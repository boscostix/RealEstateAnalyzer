"""Tests for acquisition calculations."""

from decimal import Decimal

from app.calculations.acquisition import resolve_amount_or_percent


def test_resolve_amount_or_percent_prefers_fixed_amount() -> None:
    result = resolve_amount_or_percent(
        Decimal("100000"),
        Decimal("2500"),
        Decimal("3"),
    )
    assert result == Decimal("2500.00")


def test_resolve_amount_or_percent_uses_percentage_when_fixed_missing() -> None:
    result = resolve_amount_or_percent(
        Decimal("100000"),
        None,
        Decimal("3"),
    )
    assert result == Decimal("3000.00")

