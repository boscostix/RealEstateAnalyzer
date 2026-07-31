"""Tests for the research provider registry."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.models.research import (
    CacheStatus,
    ConfidenceScore,
    ResearchDomain,
    ResearchMetadata,
    ResearchResult,
)
from app.models.verification import VerificationStatus, VerifiedField, VerifiedPropertySnapshot
from app.research.base import ResearchProvider
from app.services.research_provider_registry import ResearchProviderRegistry


def build_property() -> VerifiedPropertySnapshot:
    return VerifiedPropertySnapshot(
        source_url="https://example.com/property",
        provider="zillow",
        full_address=VerifiedField[str](
            extracted_value="123 Main St, Dallas, TX 75001",
            final_value="123 Main St, Dallas, TX 75001",
            status=VerificationStatus.VERIFIED,
        ),
        asking_price=VerifiedField[Decimal](
            extracted_value=Decimal("300000"),
            final_value=Decimal("300000"),
            status=VerificationStatus.VERIFIED,
        ),
    )


class DummyResearchProvider(ResearchProvider):
    name = "dummy_public_records"
    domain = ResearchDomain.PUBLIC_RECORDS

    def supports(self, property_snapshot: VerifiedPropertySnapshot) -> bool:
        return property_snapshot.provider == "zillow"

    async def research(
        self,
        property_snapshot: VerifiedPropertySnapshot,
    ) -> ResearchResult[Any]:
        return ResearchResult[dict[str, str]](
            provider=self.name,
            retrieved_at=ResearchMetadata(
                provider=self.name,
                domain=self.domain,
                provider_latency_ms=1,
                cache_status=CacheStatus.MISS,
            ).retrieved_at,
            metadata=ResearchMetadata(
                provider=self.name,
                domain=self.domain,
                provider_latency_ms=1,
                cache_status=CacheStatus.MISS,
            ),
            confidence=ConfidenceScore(value=Decimal("1")),
            data={"status": "ok"},
        )


def test_research_registry_filters_by_domain_and_support() -> None:
    registry = ResearchProviderRegistry([DummyResearchProvider()])

    providers = registry.supported_providers(
        ResearchDomain.PUBLIC_RECORDS,
        build_property(),
    )

    assert [provider.name for provider in providers] == ["dummy_public_records"]


def test_research_registry_returns_sorted_provider_names() -> None:
    registry = ResearchProviderRegistry([DummyResearchProvider()])

    assert registry.provider_names(ResearchDomain.PUBLIC_RECORDS) == [
        "dummy_public_records"
    ]
