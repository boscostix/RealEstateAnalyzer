"""Normalized public-records research models."""

from __future__ import annotations

from datetime import date as dt_date
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.research import ConfidenceScore, ResearchField, ResearchResult
from app.models.verification import VerifiedPropertySnapshot


class LotDimensions(BaseModel):
    """Normalized lot dimensions when available from public records."""

    width_feet: Decimal | None = None
    depth_feet: Decimal | None = None
    acreage: Decimal | None = None


class TaxHistoryRecord(BaseModel):
    """One public-record tax year."""

    tax_year: int
    assessed_value: Decimal | None = None
    annual_tax_amount: Decimal | None = None
    land_assessed_value: Decimal | None = None
    improvement_assessed_value: Decimal | None = None


class OwnershipRecord(BaseModel):
    """Normalized ownership information when legally available."""

    owner_name: str
    owner_occupied: bool | None = None
    mailing_address: str | None = None
    ownership_vesting: str | None = None


class ParcelInfo(BaseModel):
    """Normalized parcel-level information."""

    parcel_number: str | None = None
    legal_description: str | None = None
    subdivision: str | None = None
    lot_square_feet: int | None = None
    lot_dimensions: LotDimensions | None = None
    zoning: str | None = None


class FloodZoneInfo(BaseModel):
    """Flood zone and FEMA designation data."""

    flood_zone: str | None = None
    fema_designation: str | None = None
    flood_map_panel: str | None = None
    effective_date: dt_date | None = None


class PermitRecord(BaseModel):
    """Permit history entry."""

    permit_number: str | None = None
    issued_date: dt_date | None = None
    description: str | None = None
    status: str | None = None
    estimated_cost: Decimal | None = None


class DeedRecord(BaseModel):
    """Deed history entry."""

    recorded_date: dt_date | None = None
    deed_type: str | None = None
    grantor: str | None = None
    grantee: str | None = None
    document_number: str | None = None


class SaleRecord(BaseModel):
    """Normalized public-record sale history entry."""

    sale_date: dt_date | None = None
    sale_price: Decimal | None = None
    buyer_name: str | None = None
    seller_name: str | None = None
    arms_length: bool | None = None
    document_number: str | None = None


class BuildingCharacteristics(BaseModel):
    """Building characteristics as reported by public records."""

    property_type: str | None = None
    year_built: int | None = None
    square_feet: int | None = None
    bedrooms: Decimal | None = None
    bathrooms: Decimal | None = None
    stories: Decimal | None = None
    construction_type: str | None = None


class ValidationComparison[T](BaseModel):
    """Comparison between verified listing data and public records."""

    listing_value: T | None = None
    public_record_value: T | None = None
    matches: bool | None = None
    difference: Decimal | None = None
    note: str | None = None


class BuildingValidation(BaseModel):
    """Validation of core building fields against public records."""

    year_built: ValidationComparison[int]
    square_feet: ValidationComparison[int]


class PublicRecordsData(BaseModel):
    """Normalized public-records payload returned by deterministic providers."""

    tax_history: ResearchField[list[TaxHistoryRecord]] = Field(
        default_factory=lambda: ResearchField[list[TaxHistoryRecord]](
            value=[],
            confidence=ConfidenceScore(value=Decimal("0")),
        )
    )
    assessed_value: ResearchField[Decimal | None]
    ownership: ResearchField[list[OwnershipRecord]] = Field(
        default_factory=lambda: ResearchField[list[OwnershipRecord]](
            value=[],
            confidence=ConfidenceScore(value=Decimal("0")),
        )
    )
    parcel: ResearchField[ParcelInfo | None]
    flood_zone: ResearchField[FloodZoneInfo | None]
    permits: ResearchField[list[PermitRecord]] = Field(
        default_factory=lambda: ResearchField[list[PermitRecord]](
            value=[],
            confidence=ConfidenceScore(value=Decimal("0")),
        )
    )
    deeds: ResearchField[list[DeedRecord]] = Field(
        default_factory=lambda: ResearchField[list[DeedRecord]](
            value=[],
            confidence=ConfidenceScore(value=Decimal("0")),
        )
    )
    sale_history: ResearchField[list[SaleRecord]] = Field(
        default_factory=lambda: ResearchField[list[SaleRecord]](
            value=[],
            confidence=ConfidenceScore(value=Decimal("0")),
        )
    )
    building_characteristics: ResearchField[BuildingCharacteristics | None]
    validations: ResearchField[BuildingValidation | None]


class PublicRecordsResearchRequest(BaseModel):
    """API request for deterministic public-records research."""

    property: VerifiedPropertySnapshot
    bypass_cache: bool = False


class PublicRecordsResearchResponse(BaseModel):
    """API response wrapper for deterministic public-records research."""

    success: bool
    result: ResearchResult[PublicRecordsData] | None = None
