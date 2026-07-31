"""Tests for research cache helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from app.models.research import (
    CacheStatus,
    ConfidenceScore,
    ResearchDomain,
    ResearchMetadata,
    ResearchResult,
)
from app.research.cache import InMemoryResearchCache


def build_result() -> ResearchResult[dict[str, str]]:
    retrieved_at = datetime.now(UTC)
    return ResearchResult[dict[str, str]](
        provider="provider",
        retrieved_at=retrieved_at,
        metadata=ResearchMetadata(
            provider="provider",
            domain=ResearchDomain.PUBLIC_RECORDS,
            retrieved_at=retrieved_at,
            provider_latency_ms=10,
            cache_status=CacheStatus.MISS,
        ),
        confidence=ConfidenceScore(value=Decimal("0.8")),
        data={"key": "value"},
    )


async def test_in_memory_cache_returns_stored_result() -> None:
    cache = InMemoryResearchCache()
    result = build_result()

    await cache.set("cache-key", result, ttl_seconds=60)
    cached = await cache.get("cache-key")

    assert cached == result


async def test_in_memory_cache_expires_entries() -> None:
    cache = InMemoryResearchCache()
    result = build_result()

    await cache.set("cache-key", result, ttl_seconds=0)

    assert await cache.get("cache-key") is None
