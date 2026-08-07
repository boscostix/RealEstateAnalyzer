"""Tests for the deterministic neighborhood research service."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.exceptions import NeighborhoodUnavailableError, ResearchProviderError
from app.models.neighborhood import (
    AmenityRecord,
    CommuteTimeRecord,
    CrimeStatistics,
    DevelopmentRecord,
    EmployerRecord,
    EnvironmentalHazardRecord,
    FloodRiskSummary,
    NeighborhoodData,
    NeighborhoodResearchRequest,
    PopulationIncomeStats,
    SchoolRecord,
    ZoningChangeRecord,
)
from app.models.research import (
    CacheStatus,
    ConfidenceScore,
    ResearchDomain,
    ResearchField,
    ResearchMetadata,
    ResearchResult,
)
from app.models.verification import VerificationStatus, VerifiedField, VerifiedPropertySnapshot
from app.research.cache import InMemoryResearchCache
from app.research.neighborhood_base import NeighborhoodProvider
from app.services.neighborhood_service import NeighborhoodService
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


def build_result(provider: str) -> ResearchResult[NeighborhoodData]:
    retrieved_at = datetime.now(UTC)
    return ResearchResult[NeighborhoodData](
        provider=provider,
        retrieved_at=retrieved_at,
        metadata=ResearchMetadata(
            provider=provider,
            domain=ResearchDomain.NEIGHBORHOOD,
            retrieved_at=retrieved_at,
            provider_latency_ms=5,
            cache_status=CacheStatus.MISS,
            source_url="https://city.example.gov/neighborhood",
            source_name="City Neighborhood Data",
        ),
        confidence=ConfidenceScore(value=Decimal("0.82")),
        data=NeighborhoodData(
            nearby_schools=ResearchField[list[SchoolRecord]](
                value=[
                    SchoolRecord(
                        name="Main Elementary",
                        level="elementary",
                        rating=Decimal("8.5"),
                        distance_miles=Decimal("0.8"),
                    )
                ],
                confidence=ConfidenceScore(value=Decimal("0.85")),
            ),
            school_rating_average=ResearchField[Decimal | None](
                value=Decimal("8.5"),
                confidence=ConfidenceScore(value=Decimal("0.85")),
            ),
            commute_times=ResearchField[list[CommuteTimeRecord]](
                value=[
                    CommuteTimeRecord(
                        destination_name="Downtown Dallas",
                        mode="drive",
                        minutes=28,
                    )
                ],
                confidence=ConfidenceScore(value=Decimal("0.75")),
            ),
            walk_score=ResearchField[Decimal | None](
                value=Decimal("62"),
                confidence=ConfidenceScore(value=Decimal("0.8")),
            ),
            transit_score=ResearchField[Decimal | None](
                value=Decimal("41"),
                confidence=ConfidenceScore(value=Decimal("0.7")),
            ),
            bike_score=ResearchField[Decimal | None](
                value=Decimal("55"),
                confidence=ConfidenceScore(value=Decimal("0.7")),
            ),
            nearby_employers=ResearchField[list[EmployerRecord]](
                value=[
                    EmployerRecord(
                        name="Tech Campus",
                        distance_miles=Decimal("2.4"),
                        category="office",
                    )
                ],
                confidence=ConfidenceScore(value=Decimal("0.7")),
            ),
            major_employers=ResearchField[list[EmployerRecord]](
                value=[EmployerRecord(name="DFW Airport", category="transportation")],
                confidence=ConfidenceScore(value=Decimal("0.65")),
            ),
            demographics=ResearchField[PopulationIncomeStats | None](
                value=PopulationIncomeStats(
                    population=18500,
                    median_household_income=Decimal("78500"),
                ),
                confidence=ConfidenceScore(value=Decimal("0.8")),
            ),
            crime_statistics=ResearchField[CrimeStatistics | None](
                value=CrimeStatistics(
                    violent_crime_index=Decimal("0.42"),
                    property_crime_index=Decimal("0.58"),
                    overall_crime_index=Decimal("0.50"),
                ),
                confidence=ConfidenceScore(value=Decimal("0.72")),
            ),
            flood_risk=ResearchField[FloodRiskSummary | None](
                value=FloodRiskSummary(
                    risk_level="moderate",
                    in_flood_plain=False,
                    fema_designation="Zone X",
                ),
                confidence=ConfidenceScore(value=Decimal("0.76")),
            ),
            environmental_hazards=ResearchField[list[EnvironmentalHazardRecord]](
                value=[
                    EnvironmentalHazardRecord(
                        hazard_type="industrial_site",
                        distance_miles=Decimal("3.1"),
                        severity="low",
                        status="monitored",
                    )
                ],
                confidence=ConfidenceScore(value=Decimal("0.6")),
            ),
            nearby_developments=ResearchField[list[DevelopmentRecord]](
                value=[
                    DevelopmentRecord(
                        name="Mixed Use Village",
                        category="mixed_use",
                        distance_miles=Decimal("1.8"),
                        status="planned",
                    )
                ],
                confidence=ConfidenceScore(value=Decimal("0.7")),
            ),
            zoning_changes=ResearchField[list[ZoningChangeRecord]](
                value=[
                    ZoningChangeRecord(
                        title="Corridor rezoning study",
                        status="proposed",
                        distance_miles=Decimal("2.0"),
                    )
                ],
                confidence=ConfidenceScore(value=Decimal("0.65")),
            ),
            shopping=ResearchField[list[AmenityRecord]](
                value=[
                    AmenityRecord(
                        name="Market Plaza",
                        category="shopping",
                        distance_miles=Decimal("1.2"),
                    )
                ],
                confidence=ConfidenceScore(value=Decimal("0.8")),
            ),
            hospitals=ResearchField[list[AmenityRecord]](
                value=[
                    AmenityRecord(
                        name="Regional Medical Center",
                        category="hospital",
                        distance_miles=Decimal("4.3"),
                    )
                ],
                confidence=ConfidenceScore(value=Decimal("0.75")),
            ),
            parks=ResearchField[list[AmenityRecord]](
                value=[
                    AmenityRecord(
                        name="Sunnybrook Park",
                        category="park",
                        distance_miles=Decimal("0.6"),
                    )
                ],
                confidence=ConfidenceScore(value=Decimal("0.8")),
            ),
        ),
    )


class FailingNeighborhoodProvider(NeighborhoodProvider):
    name = "failing_neighborhood"

    def supports(self, property_snapshot: VerifiedPropertySnapshot) -> bool:
        return True

    async def research(
        self,
        property_snapshot: VerifiedPropertySnapshot,
    ) -> ResearchResult[NeighborhoodData]:
        raise ResearchProviderError(message="Primary neighborhood provider failed.")


class SuccessfulNeighborhoodProvider(NeighborhoodProvider):
    name = "neighborhood_provider"

    def supports(self, property_snapshot: VerifiedPropertySnapshot) -> bool:
        return True

    async def research(
        self,
        property_snapshot: VerifiedPropertySnapshot,
    ) -> ResearchResult[NeighborhoodData]:
        return build_result(self.name)


@pytest.mark.asyncio
async def test_neighborhood_service_uses_provider_fallback_and_cache() -> None:
    service = NeighborhoodService(
        registry=ResearchProviderRegistry(
            [FailingNeighborhoodProvider(), SuccessfulNeighborhoodProvider()]
        ),
        cache=InMemoryResearchCache(),
    )
    request = NeighborhoodResearchRequest(property=build_property())

    first = await service.research(request)
    second = await service.research(request)

    assert first.result is not None
    assert second.result is not None
    assert first.result.provider == "neighborhood_provider"
    assert first.result.metadata.cache_status == CacheStatus.MISS
    assert second.result.metadata.cache_status == CacheStatus.HIT
    assert "failing_neighborhood:research_provider_error" in first.result.metadata.warnings


@pytest.mark.asyncio
async def test_neighborhood_service_raises_when_no_provider_is_available() -> None:
    service = NeighborhoodService(registry=ResearchProviderRegistry())

    with pytest.raises(NeighborhoodUnavailableError):
        await service.research(NeighborhoodResearchRequest(property=build_property()))
