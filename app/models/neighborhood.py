"""Normalized neighborhood research models."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.research import ConfidenceScore, ResearchField, ResearchResult
from app.models.verification import VerifiedPropertySnapshot


class SchoolRecord(BaseModel):
    """Nearby school information."""

    name: str
    level: str | None = None
    rating: Decimal | None = None
    distance_miles: Decimal | None = None


class CommuteTimeRecord(BaseModel):
    """Commute time to a destination."""

    destination_name: str
    mode: str
    minutes: int | None = None


class EmployerRecord(BaseModel):
    """Nearby or major employer."""

    name: str
    distance_miles: Decimal | None = None
    employee_count_estimate: int | None = None
    category: str | None = None


class PopulationIncomeStats(BaseModel):
    """Neighborhood demographic metrics."""

    population: int | None = None
    median_household_income: Decimal | None = None


class CrimeStatistics(BaseModel):
    """Normalized crime metrics."""

    violent_crime_index: Decimal | None = None
    property_crime_index: Decimal | None = None
    overall_crime_index: Decimal | None = None


class FloodRiskSummary(BaseModel):
    """Flood-related neighborhood risk information."""

    risk_level: str | None = None
    in_flood_plain: bool | None = None
    fema_designation: str | None = None


class EnvironmentalHazardRecord(BaseModel):
    """Environmental hazard near the subject property."""

    hazard_type: str
    distance_miles: Decimal | None = None
    severity: str | None = None
    status: str | None = None


class DevelopmentRecord(BaseModel):
    """Nearby development or planning change."""

    name: str
    category: str | None = None
    distance_miles: Decimal | None = None
    status: str | None = None


class ZoningChangeRecord(BaseModel):
    """Zoning changes affecting the neighborhood."""

    title: str
    status: str | None = None
    distance_miles: Decimal | None = None


class AmenityRecord(BaseModel):
    """Normalized amenity location."""

    name: str
    category: str
    distance_miles: Decimal | None = None


class NeighborhoodData(BaseModel):
    """Normalized neighborhood research payload."""

    nearby_schools: ResearchField[list[SchoolRecord]] = Field(
        default_factory=lambda: ResearchField[list[SchoolRecord]](
            value=[],
            confidence=ConfidenceScore(value=Decimal("0")),
        )
    )
    school_rating_average: ResearchField[Decimal | None]
    commute_times: ResearchField[list[CommuteTimeRecord]] = Field(
        default_factory=lambda: ResearchField[list[CommuteTimeRecord]](
            value=[],
            confidence=ConfidenceScore(value=Decimal("0")),
        )
    )
    walk_score: ResearchField[Decimal | None]
    transit_score: ResearchField[Decimal | None]
    bike_score: ResearchField[Decimal | None]
    nearby_employers: ResearchField[list[EmployerRecord]] = Field(
        default_factory=lambda: ResearchField[list[EmployerRecord]](
            value=[],
            confidence=ConfidenceScore(value=Decimal("0")),
        )
    )
    major_employers: ResearchField[list[EmployerRecord]] = Field(
        default_factory=lambda: ResearchField[list[EmployerRecord]](
            value=[],
            confidence=ConfidenceScore(value=Decimal("0")),
        )
    )
    demographics: ResearchField[PopulationIncomeStats | None]
    crime_statistics: ResearchField[CrimeStatistics | None]
    flood_risk: ResearchField[FloodRiskSummary | None]
    environmental_hazards: ResearchField[list[EnvironmentalHazardRecord]] = Field(
        default_factory=lambda: ResearchField[list[EnvironmentalHazardRecord]](
            value=[],
            confidence=ConfidenceScore(value=Decimal("0")),
        )
    )
    nearby_developments: ResearchField[list[DevelopmentRecord]] = Field(
        default_factory=lambda: ResearchField[list[DevelopmentRecord]](
            value=[],
            confidence=ConfidenceScore(value=Decimal("0")),
        )
    )
    zoning_changes: ResearchField[list[ZoningChangeRecord]] = Field(
        default_factory=lambda: ResearchField[list[ZoningChangeRecord]](
            value=[],
            confidence=ConfidenceScore(value=Decimal("0")),
        )
    )
    shopping: ResearchField[list[AmenityRecord]] = Field(
        default_factory=lambda: ResearchField[list[AmenityRecord]](
            value=[],
            confidence=ConfidenceScore(value=Decimal("0")),
        )
    )
    hospitals: ResearchField[list[AmenityRecord]] = Field(
        default_factory=lambda: ResearchField[list[AmenityRecord]](
            value=[],
            confidence=ConfidenceScore(value=Decimal("0")),
        )
    )
    parks: ResearchField[list[AmenityRecord]] = Field(
        default_factory=lambda: ResearchField[list[AmenityRecord]](
            value=[],
            confidence=ConfidenceScore(value=Decimal("0")),
        )
    )


class NeighborhoodResearchRequest(BaseModel):
    """API request for neighborhood research."""

    property: VerifiedPropertySnapshot
    bypass_cache: bool = False


class NeighborhoodResearchResponse(BaseModel):
    """API response wrapper for neighborhood research."""

    success: bool
    result: ResearchResult[NeighborhoodData] | None = None
