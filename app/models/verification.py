"""Models for property verification and correction."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.models.extraction import PropertyExtractionResult


class VerificationStatus(StrEnum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    CORRECTED = "corrected"
    ESTIMATED = "estimated"
    MISSING = "missing"
    CONFLICTING = "conflicting"


class VerifiedField[T](BaseModel):
    """Represents extracted and final values for one verified field."""

    extracted_value: T | None = None
    final_value: T | None = None
    status: VerificationStatus
    source: str | None = None
    confidence: Decimal | None = None
    user_modified: bool = False


class VerifiedPropertySnapshot(BaseModel):
    """Property fields used by the underwriting engine."""

    source_url: str
    provider: str
    full_address: VerifiedField[str] = Field(
        default_factory=lambda: VerifiedField[str](status=VerificationStatus.MISSING)
    )
    asking_price: VerifiedField[Decimal] = Field(
        default_factory=lambda: VerifiedField[Decimal](status=VerificationStatus.MISSING)
    )
    bedrooms: VerifiedField[Decimal] = Field(
        default_factory=lambda: VerifiedField[Decimal](status=VerificationStatus.MISSING)
    )
    bathrooms: VerifiedField[Decimal] = Field(
        default_factory=lambda: VerifiedField[Decimal](status=VerificationStatus.MISSING)
    )
    square_feet: VerifiedField[int] = Field(
        default_factory=lambda: VerifiedField[int](status=VerificationStatus.MISSING)
    )
    lot_square_feet: VerifiedField[int] = Field(
        default_factory=lambda: VerifiedField[int](status=VerificationStatus.MISSING)
    )
    year_built: VerifiedField[int] = Field(
        default_factory=lambda: VerifiedField[int](status=VerificationStatus.MISSING)
    )
    annual_property_tax: VerifiedField[Decimal] = Field(
        default_factory=lambda: VerifiedField[Decimal](status=VerificationStatus.MISSING)
    )
    annual_hoa: VerifiedField[Decimal] = Field(
        default_factory=lambda: VerifiedField[Decimal](status=VerificationStatus.MISSING)
    )
    property_type: VerifiedField[str] = Field(
        default_factory=lambda: VerifiedField[str](status=VerificationStatus.MISSING)
    )


class PropertyVerificationRequest(BaseModel):
    """Request payload for verifying extracted property data."""

    extraction: PropertyExtractionResult
    corrections: dict[str, Any] = Field(default_factory=dict)
    confirmed_fields: list[str] = Field(default_factory=list)


class VerificationSummary(BaseModel):
    verified_fields: list[str] = Field(default_factory=list)
    corrected_fields: list[str] = Field(default_factory=list)
    unverified_fields: list[str] = Field(default_factory=list)
    estimated_fields: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    conflicting_fields: list[str] = Field(default_factory=list)


class PropertyVerificationResponse(BaseModel):
    success: bool
    property: VerifiedPropertySnapshot | None = None
    verification_summary: VerificationSummary | None = None
