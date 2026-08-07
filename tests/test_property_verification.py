"""Tests for property verification workflows."""

from __future__ import annotations

from decimal import Decimal

from app.models.extraction import (
    ExtractedField,
    ExtractionMetadata,
    PropertyExtractionResult,
)
from app.models.property import Address, NormalizedProperty
from app.models.verification import PropertyVerificationRequest, VerificationStatus
from app.services.property_verification_service import PropertyVerificationService


def test_property_verification_marks_confirmed_and_corrected_fields() -> None:
    extraction = PropertyExtractionResult(
        provider="zillow",
        source_url="https://www.zillow.com/example",
        property=NormalizedProperty(
            source_url="https://www.zillow.com/example",
            provider="zillow",
            address=Address(full_address="123 Main St, Dallas, TX 75001"),
            asking_price=Decimal("300000"),
            bedrooms=Decimal("3"),
            bathrooms=Decimal("2"),
            square_feet=1500,
            annual_property_tax=Decimal("4500"),
        ),
        metadata=ExtractionMetadata(
            extraction_method="hasdata_api",
            fields_found=6,
            fields_missing=[],
            warnings=[],
        ),
        field_provenance={
            "address.full_address": ExtractedField[str](
                value="123 Main St, Dallas, TX 75001",
                source="hasdata_api",
                confidence=0.99,
            ),
            "asking_price": ExtractedField[Decimal](
                value=Decimal("300000"),
                source="hasdata_api",
                confidence=0.99,
            ),
            "annual_property_tax": ExtractedField[Decimal](
                value=Decimal("4500"),
                source="hasdata_api",
                confidence=0.75,
            ),
        },
    )
    request = PropertyVerificationRequest(
        extraction=extraction,
        corrections={"annual_property_tax": Decimal("5000")},
        confirmed_fields=["asking_price"],
    )

    response = PropertyVerificationService().verify(request)

    assert response.success is True
    assert response.property is not None
    assert response.verification_summary is not None
    assert response.property.asking_price.status == VerificationStatus.VERIFIED
    assert response.property.annual_property_tax.status == VerificationStatus.CORRECTED
    assert response.property.annual_property_tax.final_value == Decimal("5000")
    assert "asking_price" in response.verification_summary.verified_fields
    assert "annual_property_tax" in response.verification_summary.corrected_fields


def test_property_verification_falls_back_to_extracted_property_values() -> None:
    extraction = PropertyExtractionResult(
        provider="zillow",
        source_url="https://www.zillow.com/example",
        property=NormalizedProperty(
            source_url="https://www.zillow.com/example",
            provider="zillow",
            address=Address(full_address="123 Main St, Dallas, TX 75001"),
            asking_price=Decimal("300000"),
            bedrooms=Decimal("3"),
            bathrooms=Decimal("2"),
            year_built=1985,
            property_type="single_family",
        ),
        metadata=ExtractionMetadata(
            extraction_method="hasdata_api",
            fields_found=6,
            fields_missing=[],
            warnings=[],
        ),
    )
    request = PropertyVerificationRequest(
        extraction=extraction,
        confirmed_fields=["asking_price", "full_address"],
    )

    response = PropertyVerificationService().verify(request)

    assert response.success is True
    assert response.property is not None
    assert response.property.full_address.status == VerificationStatus.VERIFIED
    assert response.property.asking_price.status == VerificationStatus.VERIFIED
    assert response.property.bedrooms.status == VerificationStatus.UNVERIFIED
    assert response.property.property_type.final_value == "single_family"
