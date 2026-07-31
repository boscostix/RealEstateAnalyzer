"""Tests for shared research models."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models.research import (
    CacheStatus,
    Citation,
    ConfidenceScore,
    ResearchDomain,
    ResearchField,
    ResearchMetadata,
    ResearchResult,
    Source,
    SourceType,
)


def test_confidence_score_rejects_values_above_one() -> None:
    with pytest.raises(ValidationError):
        ConfidenceScore(value=Decimal("1.1"))


def test_research_result_captures_common_shape() -> None:
    retrieved_at = datetime.now(UTC)
    citation = Citation(
        source_name="County API",
        source_url="https://county.example.gov/parcel/123",
        source_type=SourceType.GOVERNMENT,
    )
    source = Source(
        name="County API",
        type=SourceType.GOVERNMENT,
        url="https://county.example.gov/parcel/123",
    )
    metadata = ResearchMetadata(
        provider="county_api",
        domain=ResearchDomain.PUBLIC_RECORDS,
        retrieved_at=retrieved_at,
        provider_latency_ms=125,
        cache_status=CacheStatus.MISS,
        source_url=source.url,
        source_name=source.name,
    )

    result = ResearchResult[dict[str, ResearchField[str]]](
        provider="county_api",
        retrieved_at=retrieved_at,
        metadata=metadata,
        confidence=ConfidenceScore(value=Decimal("0.82"), reason="Two authoritative fields"),
        citations=[citation],
        sources=[source],
        data={
            "zoning": ResearchField[str](
                value="R-1",
                confidence=ConfidenceScore(value=Decimal("0.90")),
                citations=[citation],
            )
        },
    )

    assert result.provider == "county_api"
    assert result.metadata.cache_status == CacheStatus.MISS
    assert result.data["zoning"].value == "R-1"
