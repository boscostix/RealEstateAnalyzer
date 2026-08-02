"""Tests for return metric helpers."""

from decimal import Decimal

from app.calculations.returns import safe_divide


def test_safe_divide_returns_none_for_zero_denominator() -> None:
    assert safe_divide(Decimal("10"), Decimal("0")) is None


def test_safe_divide_returns_decimal_for_nonzero_denominator() -> None:
    assert safe_divide(Decimal("10"), Decimal("2")) == Decimal("5")
