"""Tests for research validation helpers."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.exceptions import ResearchValidationError
from app.utils.research_validation import (
    combine_confidence_scores,
    validate_confidence_value,
    validate_provider_latency,
    validate_source_url,
)


def test_validate_confidence_value_accepts_valid_score() -> None:
    assert validate_confidence_value(Decimal("0.75")) == Decimal("0.75")


def test_validate_confidence_value_rejects_invalid_score() -> None:
    with pytest.raises(ResearchValidationError):
        validate_confidence_value(Decimal("1.5"), field_name="overall_confidence")


def test_validate_provider_latency_rejects_negative_values() -> None:
    with pytest.raises(ResearchValidationError):
        validate_provider_latency(-1)


def test_validate_source_url_rejects_non_http_url() -> None:
    with pytest.raises(ResearchValidationError):
        validate_source_url("ftp://example.com/data")


def test_combine_confidence_scores_averages_values() -> None:
    combined = combine_confidence_scores([Decimal("0.6"), Decimal("0.8")])

    assert combined == Decimal("0.7")
