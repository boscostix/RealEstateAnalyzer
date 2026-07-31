"""Normalized comparable property research models."""

from __future__ import annotations

from datetime import date as dt_date
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field

from app.models.research import ResearchResult
from app.models.verification import VerifiedPropertySnapshot


class RentalStatus(StrEnum):
    """Supported rental comparable listing statuses."""

    ACTIVE = "active"
    LEASED = "leased"


class ValueRange(BaseModel):
    """Simple low/high deterministic range."""

    low: Decimal | None = None
    high: Decimal | None = None


class SalesComparableRecord(BaseModel):
    """Normalized sales comparable candidate."""

    address: str
    source_url: str | None = None
    sold_date: dt_date | None = None
    sold_price: Decimal | None = None
    list_price: Decimal | None = None
    square_feet: int | None = None
    bedrooms: Decimal | None = None
    bathrooms: Decimal | None = None
    year_built: int | None = None
    distance_miles: Decimal | None = None
    price_per_square_foot: Decimal | None = None
    adjusted_price_per_square_foot: Decimal | None = None
    similarity_score: Decimal | None = None


class RentalComparableRecord(BaseModel):
    """Normalized rental comparable candidate."""

    address: str
    source_url: str | None = None
    rental_status: RentalStatus
    listed_date: dt_date | None = None
    leased_date: dt_date | None = None
    monthly_rent: Decimal | None = None
    square_feet: int | None = None
    bedrooms: Decimal | None = None
    bathrooms: Decimal | None = None
    year_built: int | None = None
    distance_miles: Decimal | None = None
    rent_per_square_foot: Decimal | None = None
    occupancy_indicator: Decimal | None = None
    similarity_score: Decimal | None = None


class SalesCompsFilters(BaseModel):
    """Deterministic filters for sales comparable selection."""

    max_distance_miles: Decimal = Decimal("5")
    max_square_feet_delta_ratio: Decimal = Decimal("0.25")
    max_bedroom_delta: Decimal = Decimal("1")
    max_bathroom_delta: Decimal = Decimal("1")
    max_year_built_delta: int = 20
    sold_within_days: int = 365
    limit: int = 5
    reference_date: dt_date = Field(default_factory=dt_date.today)


class RentalCompsFilters(BaseModel):
    """Deterministic filters for rental comparable selection."""

    max_distance_miles: Decimal = Decimal("5")
    max_square_feet_delta_ratio: Decimal = Decimal("0.25")
    max_bedroom_delta: Decimal = Decimal("1")
    max_bathroom_delta: Decimal = Decimal("1")
    max_year_built_delta: int = 20
    include_active: bool = True
    include_leased: bool = True
    limit: int = 5
    reference_date: dt_date = Field(default_factory=dt_date.today)


class SalesCompsSummary(BaseModel):
    """Aggregate statistics derived from filtered sales comparables."""

    comparable_count: int
    average_sold_price: Decimal | None = None
    median_sold_price: Decimal | None = None
    average_price_per_square_foot: Decimal | None = None
    median_adjusted_price_per_square_foot: Decimal | None = None
    sold_price_range: ValueRange = Field(default_factory=ValueRange)


class RentalCompsSummary(BaseModel):
    """Aggregate statistics derived from filtered rental comparables."""

    comparable_count: int
    average_monthly_rent: Decimal | None = None
    median_monthly_rent: Decimal | None = None
    average_rent_per_square_foot: Decimal | None = None
    estimated_rent_range: ValueRange = Field(default_factory=ValueRange)
    active_count: int = 0
    leased_count: int = 0
    average_occupancy_indicator: Decimal | None = None


class SalesCompsData(BaseModel):
    """Final sales comparable research payload."""

    top_comparables: list[SalesComparableRecord] = Field(default_factory=list)
    summary: SalesCompsSummary


class RentalCompsData(BaseModel):
    """Final rental comparable research payload."""

    best_comparables: list[RentalComparableRecord] = Field(default_factory=list)
    summary: RentalCompsSummary


class SalesCompsProviderData(BaseModel):
    """Raw sales comparable candidates returned by a provider."""

    comparables: list[SalesComparableRecord] = Field(default_factory=list)


class RentalCompsProviderData(BaseModel):
    """Raw rental comparable candidates returned by a provider."""

    comparables: list[RentalComparableRecord] = Field(default_factory=list)


class SalesCompsResearchRequest(BaseModel):
    """API request for sales comparable research."""

    property: VerifiedPropertySnapshot
    filters: SalesCompsFilters = Field(default_factory=SalesCompsFilters)
    bypass_cache: bool = False


class SalesCompsResearchResponse(BaseModel):
    """API response wrapper for sales comparable research."""

    success: bool
    result: ResearchResult[SalesCompsData] | None = None


class RentalCompsResearchRequest(BaseModel):
    """API request for rental comparable research."""

    property: VerifiedPropertySnapshot
    filters: RentalCompsFilters = Field(default_factory=RentalCompsFilters)
    bypass_cache: bool = False


class RentalCompsResearchResponse(BaseModel):
    """API response wrapper for rental comparable research."""

    success: bool
    result: ResearchResult[RentalCompsData] | None = None
