"""Tests for mortgage calculations."""

from decimal import Decimal

from app.calculations.mortgage import calculate_monthly_payment


def test_calculate_monthly_payment_for_zero_interest_loan() -> None:
    payment = calculate_monthly_payment(Decimal("120000"), Decimal("0"), 30)
    assert payment == Decimal("333.33")


def test_calculate_monthly_payment_for_standard_loan() -> None:
    payment = calculate_monthly_payment(Decimal("200000"), Decimal("6"), 30)
    assert payment == Decimal("1199.10")
