"""Tests for the deterministic public-records service."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.exceptions import PublicRecordsUnavailableError, ResearchProviderError
from app.models.public_records import (
    BuildingCharacteristics,
    BuildingValidation,
    FloodZoneInfo,
    OwnershipRecord,
    ParcelInfo,
    PublicRecordsData,
    PublicRecordsResearchRequest,
    SaleRecord,
    TaxHistoryRecord,
    ValidationComparison,
)
from app.models.research import (
    CacheStatus,
    ConfidenceScore,
    ResearchField,
    ResearchMetadata,
    ResearchResult,
)
from app.models.verification import VerificationStatus, VerifiedField, VerifiedPropertySnapshot
from app.research.cache import InMemoryResearchCache
from app.research.public_records_base import PublicRecordsProvider
from app.services.public_records_service import PublicRecordsService
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
        square_feet=VerifiedField[int](
            extracted_value=1500,
            final_value=1500,
            status=VerificationStatus.VERIFIED,
        ),
        year_built=VerifiedField[int](
            extracted_value=1985,
            final_value=1985,
            status=VerificationStatus.VERIFIED,
        ),
    )


def build_result(provider: str) -> ResearchResult[PublicRecordsData]:
    retrieved_at = datetime.now(UTC)
    return ResearchResult[PublicRecordsData](
        provider=provider,
        retrieved_at=retrieved_at,
        metadata=ResearchMetadata(
            provider=provider,
            domain="public_records",
            retrieved_at=retrieved_at,
            provider_latency_ms=5,
            cache_status=CacheStatus.MISS,
            source_url="https://county.example.gov/parcel/123",
            source_name="County Assessor",
        ),
        confidence=ConfidenceScore(value=Decimal("0.8")),
        data=PublicRecordsData(
            tax_history=ResearchField[list[TaxHistoryRecord]](
                value=[
                    TaxHistoryRecord(
                        tax_year=2025,
                        assessed_value=Decimal("290000"),
                        annual_tax_amount=Decimal("6500"),
                    )
                ],
                confidence=ConfidenceScore(value=Decimal("0.9")),
            ),
            assessed_value=ResearchField[Decimal | None](
                value=Decimal("290000"),
                confidence=ConfidenceScore(value=Decimal("0.9")),
            ),
            ownership=ResearchField[list[OwnershipRecord]](
                value=[OwnershipRecord(owner_name="Example Owner")],
                confidence=ConfidenceScore(value=Decimal("0.7")),
            ),
            parcel=ResearchField[ParcelInfo | None](
                value=ParcelInfo(parcel_number="123-456"),
                confidence=ConfidenceScore(value=Decimal("0.9")),
            ),
            flood_zone=ResearchField[FloodZoneInfo | None](
                value=FloodZoneInfo(
                    flood_zone="X",
                    fema_designation="Minimal Risk",
                    effective_date=date(2023, 1, 1),
                ),
                confidence=ConfidenceScore(value=Decimal("0.8")),
            ),
            permits=ResearchField(value=[], confidence=ConfidenceScore(value=Decimal("0.2"))),
            deeds=ResearchField(value=[], confidence=ConfidenceScore(value=Decimal("0.2"))),
            sale_history=ResearchField[list[SaleRecord]](
                value=[SaleRecord(sale_price=Decimal("250000"))],
                confidence=ConfidenceScore(value=Decimal("0.7")),
            ),
            building_characteristics=ResearchField[BuildingCharacteristics | None](
                value=BuildingCharacteristics(year_built=1985, square_feet=1500),
                confidence=ConfidenceScore(value=Decimal("0.9")),
            ),
            validations=ResearchField[BuildingValidation | None](
                value=BuildingValidation(
                    year_built=ValidationComparison[int](
                        listing_value=1985,
                        public_record_value=1985,
                        matches=True,
                    ),
                    square_feet=ValidationComparison[int](
                        listing_value=1500,
                        public_record_value=1500,
                        matches=True,
                        difference=Decimal("0"),
                    ),
                ),
                confidence=ConfidenceScore(value=Decimal("0.95")),
            ),
        ),
    )


class FailingPublicRecordsProvider(PublicRecordsProvider):
    name = "failing_provider"

    def supports(self, property_snapshot: VerifiedPropertySnapshot) -> bool:
        return True

    async def research(
        self,
        property_snapshot: VerifiedPropertySnapshot,
    ) -> ResearchResult[PublicRecordsData]:
        raise ResearchProviderError(message="Primary provider failed.")


class SuccessfulPublicRecordsProvider(PublicRecordsProvider):
    name = "successful_provider"

    def supports(self, property_snapshot: VerifiedPropertySnapshot) -> bool:
        return True

    async def research(
        self,
        property_snapshot: VerifiedPropertySnapshot,
    ) -> ResearchResult[PublicRecordsData]:
        return build_result(self.name)


@pytest.mark.asyncio
async def test_public_records_service_uses_provider_fallback() -> None:
    service = PublicRecordsService(
        registry=ResearchProviderRegistry(
            [FailingPublicRecordsProvider(), SuccessfulPublicRecordsProvider()]
        ),
        cache=InMemoryResearchCache(),
    )

    response = await service.research(
        PublicRecordsResearchRequest(property=build_property())
    )

    assert response.success is True
    assert response.result is not None
    assert response.result.provider == "successful_provider"
    assert "failing_provider:research_provider_error" in response.result.metadata.warnings


@pytest.mark.asyncio
async def test_public_records_service_returns_cached_result() -> None:
    service = PublicRecordsService(
        registry=ResearchProviderRegistry([SuccessfulPublicRecordsProvider()]),
        cache=InMemoryResearchCache(),
    )
    request = PublicRecordsResearchRequest(property=build_property())

    first = await service.research(request)
    second = await service.research(request)

    assert first.result is not None
    assert second.result is not None
    assert first.result.metadata.cache_status == CacheStatus.MISS
    assert second.result.metadata.cache_status == CacheStatus.HIT


@pytest.mark.asyncio
async def test_public_records_service_raises_when_no_provider_available() -> None:
    service = PublicRecordsService(
        registry=ResearchProviderRegistry(),
        cache=InMemoryResearchCache(),
    )

    with pytest.raises(PublicRecordsUnavailableError):
        await service.research(PublicRecordsResearchRequest(property=build_property()))
