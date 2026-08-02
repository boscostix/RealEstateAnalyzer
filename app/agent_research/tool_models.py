"""Typed request and response models for Phase 2 agent function tools."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.comparables import (
    RentalComparableRecord,
    RentalCompsSummary,
    SalesComparableRecord,
    SalesCompsSummary,
)
from app.models.extraction import ExtractionMetadata
from app.models.neighborhood import FloodRiskSummary, NeighborhoodData, SchoolRecord
from app.models.property import NormalizedProperty, PriceHistoryEvent, SaleHistoryEvent
from app.models.public_records import (
    BuildingCharacteristics,
    BuildingValidation,
    DeedRecord,
    FloodZoneInfo,
    OwnershipRecord,
    ParcelInfo,
    PermitRecord,
    SaleRecord,
    TaxHistoryRecord,
)
from app.models.research import CacheStatus
from app.models.verification import VerifiedPropertySnapshot


class ToolErrorDetail(BaseModel):
    """Structured tool error returned instead of free-form exception text."""

    code: str
    message: str
    retryable: bool = False


class ListingFieldProvenancePayload(BaseModel):
    """Sanitized field-level provenance for a listing field."""

    field_name: str
    value: str | int | float | Decimal | None = None
    raw_value: str | None = None
    source: str
    confidence: float


class ListingSnapshotPayload(BaseModel):
    """Sanitized listing data exposed to specialist agents."""

    provider: str
    source_url: str
    metadata: ExtractionMetadata
    property: NormalizedProperty
    field_provenance: list[ListingFieldProvenancePayload] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)


class ListingHistoryPayload(BaseModel):
    """Listing-origin history fields with evidence identifiers."""

    price_history: list[PriceHistoryEvent] = Field(default_factory=list)
    sale_history: list[SaleHistoryEvent] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)


class PublicRecordsSummaryPayload(BaseModel):
    """High-signal public-record fields plus provenance identifiers."""

    provider: str
    retrieved_at: datetime
    cache_status: CacheStatus
    source_ids: list[str] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)
    assessed_value: Decimal | None = None
    ownership: list[OwnershipRecord] = Field(default_factory=list)
    parcel: ParcelInfo | None = None
    flood_zone: FloodZoneInfo | None = None
    building_characteristics: BuildingCharacteristics | None = None
    validations: BuildingValidation | None = None
    warnings: list[str] = Field(default_factory=list)


class TaxHistoryPayload(BaseModel):
    """Tax-history and assessment fields with provenance identifiers."""

    provider: str
    retrieved_at: datetime
    source_ids: list[str] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)
    tax_history: list[TaxHistoryRecord] = Field(default_factory=list)
    assessed_value: Decimal | None = None


class PermitHistoryPayload(BaseModel):
    """Permit-history slice with provenance identifiers."""

    provider: str
    retrieved_at: datetime
    source_ids: list[str] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)
    permits: list[PermitRecord] = Field(default_factory=list)


class TransactionHistoryPayload(BaseModel):
    """Transaction-history slice with provenance identifiers."""

    provider: str
    retrieved_at: datetime
    source_ids: list[str] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)
    deeds: list[DeedRecord] = Field(default_factory=list)
    sale_history: list[SaleRecord] = Field(default_factory=list)


class SalesCompsPayload(BaseModel):
    """Sales-comparable output exposed to the comparable agent."""

    provider: str
    retrieved_at: datetime
    cache_status: CacheStatus
    source_ids: list[str] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)
    top_comparables: list[SalesComparableRecord] = Field(default_factory=list)
    summary: SalesCompsSummary
    warnings: list[str] = Field(default_factory=list)


class RentalCompsPayload(BaseModel):
    """Rental-comparable output exposed to the comparable agent."""

    provider: str
    retrieved_at: datetime
    cache_status: CacheStatus
    source_ids: list[str] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)
    best_comparables: list[RentalComparableRecord] = Field(default_factory=list)
    summary: RentalCompsSummary
    warnings: list[str] = Field(default_factory=list)


class NeighborhoodSummaryPayload(BaseModel):
    """Neighborhood summary with provenance identifiers."""

    provider: str
    retrieved_at: datetime
    cache_status: CacheStatus
    source_ids: list[str] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)
    neighborhood: NeighborhoodData
    warnings: list[str] = Field(default_factory=list)


class SchoolResearchPayload(BaseModel):
    """School subset of neighborhood research with provenance identifiers."""

    provider: str
    retrieved_at: datetime
    cache_status: CacheStatus
    source_ids: list[str] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)
    nearby_schools: list[SchoolRecord] = Field(default_factory=list)
    school_rating_average: Decimal | None = None
    warnings: list[str] = Field(default_factory=list)


class FloodResearchPayload(BaseModel):
    """Flood subset of neighborhood research with provenance identifiers."""

    provider: str
    retrieved_at: datetime
    cache_status: CacheStatus
    source_ids: list[str] = Field(default_factory=list)
    citation_ids: list[str] = Field(default_factory=list)
    flood_risk: FloodRiskSummary | None = None
    warnings: list[str] = Field(default_factory=list)


class UnderwritingSummaryPayload(BaseModel):
    """Read-only deterministic underwriting summary."""

    property: VerifiedPropertySnapshot
    purchase_price: Decimal
    monthly_scheduled_rent: Decimal
    noi: Decimal
    monthly_pre_tax_cash_flow: Decimal
    cap_rate: Decimal | None = None
    cash_on_cash_return: Decimal | None = None
    dscr: Decimal | None = None
    binding_maximum_price: Decimal | None = None
    scenario_names: list[str] = Field(default_factory=list)
    stress_test_ids: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)


class ListingSnapshotToolResponse(BaseModel):
    success: bool
    data: ListingSnapshotPayload | None = None
    error: ToolErrorDetail | None = None
    warnings: list[str] = Field(default_factory=list)


class ListingHistoryToolResponse(BaseModel):
    success: bool
    data: ListingHistoryPayload | None = None
    error: ToolErrorDetail | None = None
    warnings: list[str] = Field(default_factory=list)


class ListingFieldProvenanceToolResponse(BaseModel):
    success: bool
    data: ListingFieldProvenancePayload | None = None
    error: ToolErrorDetail | None = None
    warnings: list[str] = Field(default_factory=list)


class PublicRecordsSummaryToolResponse(BaseModel):
    success: bool
    data: PublicRecordsSummaryPayload | None = None
    error: ToolErrorDetail | None = None
    warnings: list[str] = Field(default_factory=list)


class TaxHistoryToolResponse(BaseModel):
    success: bool
    data: TaxHistoryPayload | None = None
    error: ToolErrorDetail | None = None
    warnings: list[str] = Field(default_factory=list)


class PermitHistoryToolResponse(BaseModel):
    success: bool
    data: PermitHistoryPayload | None = None
    error: ToolErrorDetail | None = None
    warnings: list[str] = Field(default_factory=list)


class TransactionHistoryToolResponse(BaseModel):
    success: bool
    data: TransactionHistoryPayload | None = None
    error: ToolErrorDetail | None = None
    warnings: list[str] = Field(default_factory=list)


class SalesCompsToolResponse(BaseModel):
    success: bool
    data: SalesCompsPayload | None = None
    error: ToolErrorDetail | None = None
    warnings: list[str] = Field(default_factory=list)


class RentalCompsToolResponse(BaseModel):
    success: bool
    data: RentalCompsPayload | None = None
    error: ToolErrorDetail | None = None
    warnings: list[str] = Field(default_factory=list)


class NeighborhoodSummaryToolResponse(BaseModel):
    success: bool
    data: NeighborhoodSummaryPayload | None = None
    error: ToolErrorDetail | None = None
    warnings: list[str] = Field(default_factory=list)


class SchoolResearchToolResponse(BaseModel):
    success: bool
    data: SchoolResearchPayload | None = None
    error: ToolErrorDetail | None = None
    warnings: list[str] = Field(default_factory=list)


class FloodResearchToolResponse(BaseModel):
    success: bool
    data: FloodResearchPayload | None = None
    error: ToolErrorDetail | None = None
    warnings: list[str] = Field(default_factory=list)


class UnderwritingSummaryToolResponse(BaseModel):
    success: bool
    data: UnderwritingSummaryPayload | None = None
    error: ToolErrorDetail | None = None
    warnings: list[str] = Field(default_factory=list)
