"""Tests for deterministic sales and rental comparable services."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.exceptions import RentalCompsUnavailableError, SalesCompsUnavailableError
from app.models.comparables import (
    RentalComparableRecord,
    RentalCompsFilters,
    RentalCompsProviderData,
    RentalCompsResearchRequest,
    RentalStatus,
    SalesComparableRecord,
    SalesCompsFilters,
    SalesCompsProviderData,
    SalesCompsResearchRequest,
)
from app.models.research import (
    CacheStatus,
    ConfidenceScore,
    ResearchMetadata,
    ResearchResult,
)
from app.models.verification import VerificationStatus, VerifiedField, VerifiedPropertySnapshot
from app.research.cache import InMemoryResearchCache
from app.research.comparables_base import RentalCompsProvider, SalesCompsProvider
from app.services.rental_comps_service import RentalCompsService
from app.services.research_provider_registry import ResearchProviderRegistry
from app.services.sales_comps_service import SalesCompsService


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
        bedrooms=VerifiedField[Decimal](
            extracted_value=Decimal("3"),
            final_value=Decimal("3"),
            status=VerificationStatus.VERIFIED,
        ),
        bathrooms=VerifiedField[Decimal](
            extracted_value=Decimal("2"),
            final_value=Decimal("2"),
            status=VerificationStatus.VERIFIED,
        ),
        square_feet=VerifiedField[int](
            extracted_value=1500,
            final_value=1500,
            status=VerificationStatus.VERIFIED,
        ),
        year_built=VerifiedField[int](
            extracted_value=1990,
            final_value=1990,
            status=VerificationStatus.VERIFIED,
        ),
    )


def build_sales_result(provider: str) -> ResearchResult[SalesCompsProviderData]:
    retrieved_at = datetime.now(UTC)
    return ResearchResult[SalesCompsProviderData](
        provider=provider,
        retrieved_at=retrieved_at,
        metadata=ResearchMetadata(
            provider=provider,
            domain="sales_comps",
            retrieved_at=retrieved_at,
            provider_latency_ms=5,
            cache_status=CacheStatus.MISS,
            source_url="https://mls.example.com/sales",
            source_name="MLS Sales",
        ),
        confidence=ConfidenceScore(value=Decimal("0.8")),
        data=SalesCompsProviderData(
            comparables=[
                SalesComparableRecord(
                    address="101 First St",
                    sold_date=date(2026, 6, 15),
                    sold_price=Decimal("305000"),
                    square_feet=1520,
                    bedrooms=Decimal("3"),
                    bathrooms=Decimal("2"),
                    year_built=1992,
                    distance_miles=Decimal("1.2"),
                ),
                SalesComparableRecord(
                    address="102 Second St",
                    sold_date=date(2026, 5, 10),
                    sold_price=Decimal("299000"),
                    square_feet=1480,
                    bedrooms=Decimal("3"),
                    bathrooms=Decimal("2"),
                    year_built=1988,
                    distance_miles=Decimal("2.0"),
                ),
                SalesComparableRecord(
                    address="200 Far Ave",
                    sold_date=date(2026, 6, 1),
                    sold_price=Decimal("310000"),
                    square_feet=1510,
                    bedrooms=Decimal("3"),
                    bathrooms=Decimal("2"),
                    year_built=1991,
                    distance_miles=Decimal("8.5"),
                ),
            ]
        ),
    )


def build_rental_result(provider: str) -> ResearchResult[RentalCompsProviderData]:
    retrieved_at = datetime.now(UTC)
    return ResearchResult[RentalCompsProviderData](
        provider=provider,
        retrieved_at=retrieved_at,
        metadata=ResearchMetadata(
            provider=provider,
            domain="rental_comps",
            retrieved_at=retrieved_at,
            provider_latency_ms=5,
            cache_status=CacheStatus.MISS,
            source_url="https://rentals.example.com/listings",
            source_name="Rental Listings",
        ),
        confidence=ConfidenceScore(value=Decimal("0.75")),
        data=RentalCompsProviderData(
            comparables=[
                RentalComparableRecord(
                    address="11 Lease Ln",
                    rental_status=RentalStatus.LEASED,
                    leased_date=date(2026, 7, 1),
                    monthly_rent=Decimal("2300"),
                    square_feet=1485,
                    bedrooms=Decimal("3"),
                    bathrooms=Decimal("2"),
                    year_built=1991,
                    distance_miles=Decimal("1.0"),
                    occupancy_indicator=Decimal("0.95"),
                ),
                RentalComparableRecord(
                    address="22 Active Dr",
                    rental_status=RentalStatus.ACTIVE,
                    listed_date=date(2026, 7, 15),
                    monthly_rent=Decimal("2400"),
                    square_feet=1510,
                    bedrooms=Decimal("3"),
                    bathrooms=Decimal("2"),
                    year_built=1989,
                    distance_miles=Decimal("1.5"),
                    occupancy_indicator=Decimal("0.90"),
                ),
                RentalComparableRecord(
                    address="99 Distant Ct",
                    rental_status=RentalStatus.ACTIVE,
                    listed_date=date(2026, 7, 20),
                    monthly_rent=Decimal("2500"),
                    square_feet=1490,
                    bedrooms=Decimal("3"),
                    bathrooms=Decimal("2"),
                    year_built=1990,
                    distance_miles=Decimal("9.0"),
                ),
            ]
        ),
    )


class FailingSalesProvider(SalesCompsProvider):
    name = "failing_sales"

    def supports(self, property_snapshot: VerifiedPropertySnapshot) -> bool:
        return True

    async def research(
        self,
        property_snapshot: VerifiedPropertySnapshot,
    ) -> ResearchResult[SalesCompsProviderData]:
        raise SalesCompsUnavailableError(message="Primary sales provider failed.")


class SuccessfulSalesProvider(SalesCompsProvider):
    name = "sales_provider"

    def supports(self, property_snapshot: VerifiedPropertySnapshot) -> bool:
        return True

    async def research(
        self,
        property_snapshot: VerifiedPropertySnapshot,
    ) -> ResearchResult[SalesCompsProviderData]:
        return build_sales_result(self.name)


class FailingRentalProvider(RentalCompsProvider):
    name = "failing_rental"

    def supports(self, property_snapshot: VerifiedPropertySnapshot) -> bool:
        return True

    async def research(
        self,
        property_snapshot: VerifiedPropertySnapshot,
    ) -> ResearchResult[RentalCompsProviderData]:
        raise RentalCompsUnavailableError(message="Primary rental provider failed.")


class SuccessfulRentalProvider(RentalCompsProvider):
    name = "rental_provider"

    def supports(self, property_snapshot: VerifiedPropertySnapshot) -> bool:
        return True

    async def research(
        self,
        property_snapshot: VerifiedPropertySnapshot,
    ) -> ResearchResult[RentalCompsProviderData]:
        return build_rental_result(self.name)


@pytest.mark.asyncio
async def test_sales_comps_service_filters_ranks_and_caches_results() -> None:
    service = SalesCompsService(
        registry=ResearchProviderRegistry([FailingSalesProvider(), SuccessfulSalesProvider()]),
        cache=InMemoryResearchCache(),
    )
    request = SalesCompsResearchRequest(
        property=build_property(),
        filters=SalesCompsFilters(reference_date=date(2026, 7, 31)),
    )

    first = await service.research(request)
    second = await service.research(request)

    assert first.result is not None
    assert second.result is not None
    assert first.result.data.summary.comparable_count == 2
    assert first.result.data.top_comparables[0].address == "101 First St"
    assert first.result.data.summary.median_sold_price == Decimal("302000.00")
    assert first.result.metadata.cache_status == CacheStatus.MISS
    assert second.result.metadata.cache_status == CacheStatus.HIT


@pytest.mark.asyncio
async def test_rental_comps_service_filters_ranks_and_summarizes_results() -> None:
    service = RentalCompsService(
        registry=ResearchProviderRegistry([FailingRentalProvider(), SuccessfulRentalProvider()]),
        cache=InMemoryResearchCache(),
    )
    request = RentalCompsResearchRequest(
        property=build_property(),
        filters=RentalCompsFilters(reference_date=date(2026, 7, 31)),
    )

    response = await service.research(request)

    assert response.result is not None
    assert response.result.data.summary.comparable_count == 2
    assert response.result.data.summary.average_monthly_rent == Decimal("2350.00")
    assert response.result.data.summary.estimated_rent_range.low == Decimal("2300.00")
    assert response.result.data.summary.active_count == 1
    assert response.result.data.summary.leased_count == 1


@pytest.mark.asyncio
async def test_sales_comps_service_raises_when_no_provider_is_available() -> None:
    service = SalesCompsService(registry=ResearchProviderRegistry())

    with pytest.raises(SalesCompsUnavailableError):
        await service.research(SalesCompsResearchRequest(property=build_property()))


@pytest.mark.asyncio
async def test_rental_comps_service_raises_when_no_provider_is_available() -> None:
    service = RentalCompsService(registry=ResearchProviderRegistry())

    with pytest.raises(RentalCompsUnavailableError):
        await service.research(RentalCompsResearchRequest(property=build_property()))
