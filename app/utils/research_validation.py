"""Shared validation helpers for deterministic research services."""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal
from urllib.parse import urlparse

from app.exceptions import ResearchValidationError


def validate_confidence_value(value: Decimal, *, field_name: str = "confidence") -> Decimal:
    """Ensure confidence scores stay within the inclusive 0..1 range."""

    if value < 0 or value > 1:
        raise ResearchValidationError(
            message=f"{field_name} must be between 0 and 1.",
            field=field_name,
        )
    return value


def validate_provider_latency(value: int) -> int:
    """Ensure provider latency is non-negative."""

    if value < 0:
        raise ResearchValidationError(
            message="provider_latency_ms must be non-negative.",
            field="provider_latency_ms",
        )
    return value


def validate_source_url(url: str) -> str:
    """Ensure a source URL is HTTP(S) and has a hostname."""

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ResearchValidationError(
            message="source_url must be a valid HTTP or HTTPS URL.",
            field="source_url",
        )
    return url


def combine_confidence_scores(values: Iterable[Decimal]) -> Decimal:
    """Average field-level confidences into one overall score."""

    collected = [validate_confidence_value(value) for value in values]
    if not collected:
        raise ResearchValidationError(
            message="At least one confidence score is required.",
            field="confidence",
        )
    return sum(collected, start=Decimal("0")) / Decimal(len(collected))
