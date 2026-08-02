"""Tests for the non-AI research orchestrator."""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.exceptions import ResearchProviderError
from app.models.comparables import (
    RentalComparableRecord,
    RentalCompsData,
    RentalCompsResearchResponse,
    RentalCompsSummary,
    RentalStatus,
    SalesComparableRecord,
    SalesCompsData,
    SalesCompsResearchResponse,
    SalesCompsSummary,
)
from app.models.neighborhood import (
    NeighborhoodData,
    NeighborhoodResearchResponse,
    SchoolRecord,
)
from app.models.public_records import (
    PublicRecordsData,
    PublicRecordsResearchResponse,
)
from app.models.research import (
    CacheStatus,
    Citation,
    ConfidenceScore,
    ResearchField,
    ResearchMetadata,
    ResearchResult,
    SourceType,
)
from app.models.research_package import ResearchPackageRequest
from app.models.verification import VerificationStatus, VerifiedField, VerifiedPropertySnapshot
from app.research.config import CacheConfig, ProviderExecutionConfig, ResearchConfig
from app.services.research_orchestrator import ResearchOrchestrator


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


def build_citation() -> Citation:
    return Citation(
        source_name="Unified Source",
        source_url="https://example.com/source",
        source_type=SourceType.API,
    )


def build_public_records_response() -> PublicRecordsResearchResponse:
    retrieved_at = datetime.now(UTC)
    citation = build_citation()
    return PublicRecordsResearchResponse(
        success=True,
        result=ResearchResult[PublicRecordsData](
            provider="public_records_provider",
            retrieved_at=retrieved_at,
            metadata=ResearchMetadata(
                provider="public_records_provider",
                domain="public_records",
                retrieved_at=retrieved_at,
                provider_latency_ms=5,
                cache_status=CacheStatus.MISS,
                source_url="https://example.com/source",
                source_name="Unified Source",
            ),
            confidence=ConfidenceScore(value=Decimal("0.8")),
            citations=[citation],
            data=PublicRecordsData(
                assessed_value=ResearchField[Decimal | None](
                    value=Decimal("290000"),
                    confidence=ConfidenceScore(value=Decimal("0.8")),
                ),
                parcel=ResearchField(
                    value=None,
                    confidence=ConfidenceScore(value=Decimal("0")),
                ),
                flood_zone=ResearchField(
                    value=None,
                    confidence=ConfidenceScore(value=Decimal("0")),
                ),
                building_characteristics=ResearchField(
                    value=None,
                    confidence=ConfidenceScore(value=Decimal("0")),
                ),
                validations=ResearchField(
                    value=None,
                    confidence=ConfidenceScore(value=Decimal("0")),
                ),
            ),
        ),
    )


def build_sales_response() -> SalesCompsResearchResponse:
    retrieved_at = datetime.now(UTC)
    citation = build_citation()
    return SalesCompsResearchResponse(
        success=True,
        result=ResearchResult[SalesCompsData](
            provider="sales_provider",
            retrieved_at=retrieved_at,
            metadata=ResearchMetadata(
                provider="sales_provider",
                domain="sales_comps",
                retrieved_at=retrieved_at,
                provider_latency_ms=5,
                cache_status=CacheStatus.MISS,
                source_url="https://example.com/source",
                source_name="Unified Source",
            ),
            confidence=ConfidenceScore(value=Decimal("0.7")),
            citations=[citation],
            data=SalesCompsData(
                top_comparables=[
                    SalesComparableRecord(
                        address="101 First St",
                        sold_date=date(2026, 7, 1),
                        sold_price=Decimal("305000"),
                    )
                ],
                summary=SalesCompsSummary(comparable_count=1),
            ),
        ),
    )


def build_rental_response() -> RentalCompsResearchResponse:
    retrieved_at = datetime.now(UTC)
    citation = build_citation()
    return RentalCompsResearchResponse(
        success=True,
        result=ResearchResult[RentalCompsData](
            provider="rental_provider",
            retrieved_at=retrieved_at,
            metadata=ResearchMetadata(
                provider="rental_provider",
                domain="rental_comps",
                retrieved_at=retrieved_at,
                provider_latency_ms=5,
                cache_status=CacheStatus.MISS,
                source_url="https://example.com/source",
                source_name="Unified Source",
            ),
            confidence=ConfidenceScore(value=Decimal("0.75")),
            citations=[citation],
            data=RentalCompsData(
                best_comparables=[
                    RentalComparableRecord(
                        address="11 Lease Ln",
                        rental_status=RentalStatus.LEASED,
                        monthly_rent=Decimal("2300"),
                    )
                ],
                summary=RentalCompsSummary(comparable_count=1),
            ),
        ),
    )


def build_neighborhood_response() -> NeighborhoodResearchResponse:
    retrieved_at = datetime.now(UTC)
    citation = build_citation()
    return NeighborhoodResearchResponse(
        success=True,
        result=ResearchResult[NeighborhoodData](
            provider="neighborhood_provider",
            retrieved_at=retrieved_at,
            metadata=ResearchMetadata(
                provider="neighborhood_provider",
                domain="neighborhood",
                retrieved_at=retrieved_at,
                provider_latency_ms=5,
                cache_status=CacheStatus.MISS,
                source_url="https://example.com/source",
                source_name="Unified Source",
            ),
            confidence=ConfidenceScore(value=Decimal("0.78")),
            citations=[citation],
            data=NeighborhoodData(
                school_rating_average=ResearchField[Decimal | None](
                    value=Decimal("8.5"),
                    confidence=ConfidenceScore(value=Decimal("0.8")),
                ),
                walk_score=ResearchField[Decimal | None](
                    value=Decimal("62"),
                    confidence=ConfidenceScore(value=Decimal("0.75")),
                ),
                transit_score=ResearchField[Decimal | None](
                    value=Decimal("41"),
                    confidence=ConfidenceScore(value=Decimal("0.7")),
                ),
                bike_score=ResearchField[Decimal | None](
                    value=Decimal("55"),
                    confidence=ConfidenceScore(value=Decimal("0.7")),
                ),
                demographics=ResearchField(
                    value=None,
                    confidence=ConfidenceScore(value=Decimal("0")),
                ),
                crime_statistics=ResearchField(
                    value=None,
                    confidence=ConfidenceScore(value=Decimal("0")),
                ),
                flood_risk=ResearchField(
                    value=None,
                    confidence=ConfidenceScore(value=Decimal("0")),
                ),
                nearby_schools=ResearchField[list[SchoolRecord]](
                    value=[SchoolRecord(name="Main Elementary")],
                    confidence=ConfidenceScore(value=Decimal("0.8")),
                ),
            ),
        ),
    )


class StaticService[T]:
    def __init__(self, response: T) -> None:
        self.response = response

    async def research(self, request: object) -> T:
        return self.response


class RetryService:
    def __init__(self) -> None:
        self.calls = 0

    async def research(self, request: object) -> SalesCompsResearchResponse:
        self.calls += 1
        if self.calls == 1:
            raise ResearchProviderError(message="Transient sales issue.")
        return build_sales_response()


class TimeoutService:
    async def research(self, request: object) -> NeighborhoodResearchResponse:
        await asyncio.sleep(0.05)
        return build_neighborhood_response()


@pytest.mark.asyncio
async def test_research_orchestrator_assembles_package_and_dedupes_citations() -> None:
    orchestrator = ResearchOrchestrator(
        public_records_service=StaticService(build_public_records_response()),
        sales_comps_service=StaticService(build_sales_response()),
        rental_comps_service=StaticService(build_rental_response()),
        neighborhood_service=StaticService(build_neighborhood_response()),
    )

    response = await orchestrator.research(ResearchPackageRequest(property=build_property()))

    assert response.success is True
    assert response.package is not None
    assert response.package.public_records is not None
    assert response.package.sales_comps is not None
    assert response.package.rental_comps is not None
    assert response.package.neighborhood is not None
    assert len(response.package.metadata.completed_domains) == 4
    assert response.package.metadata.failed_domains == []
    assert len(response.package.metadata.citations) == 1


@pytest.mark.asyncio
async def test_research_orchestrator_retries_retryable_errors_and_returns_partials() -> None:
    retry_service = RetryService()
    orchestrator = ResearchOrchestrator(
        public_records_service=StaticService(build_public_records_response()),
        sales_comps_service=retry_service,
        rental_comps_service=StaticService(build_rental_response()),
        neighborhood_service=StaticService(build_neighborhood_response()),
        config=ResearchConfig(
            cache=CacheConfig(),
            execution=ProviderExecutionConfig(
                timeout_seconds=1,
                max_retries=1,
                parallelism_limit=4,
            ),
        ),
    )

    response = await orchestrator.research(ResearchPackageRequest(property=build_property()))

    assert response.package is not None
    assert response.package.sales_comps is not None
    assert retry_service.calls == 2
    assert any(warning.code == "research_provider_error" for warning in response.package.warnings)


@pytest.mark.asyncio
async def test_research_orchestrator_records_timeout_as_warning() -> None:
    orchestrator = ResearchOrchestrator(
        public_records_service=StaticService(build_public_records_response()),
        sales_comps_service=StaticService(build_sales_response()),
        rental_comps_service=StaticService(build_rental_response()),
        neighborhood_service=TimeoutService(),
        config=ResearchConfig(
            cache=CacheConfig(),
            execution=ProviderExecutionConfig(
                timeout_seconds=0.01,
                max_retries=0,
                parallelism_limit=4,
            ),
        ),
    )

    response = await orchestrator.research(ResearchPackageRequest(property=build_property()))

    assert response.package is not None
    assert response.package.neighborhood is None
    assert "neighborhood" in response.package.metadata.failed_domains
    assert any(warning.code == "research_timeout" for warning in response.package.warnings)
