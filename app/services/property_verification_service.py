"""Service for turning extraction output into a verified property snapshot."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.models.extraction import ExtractedField, PropertyExtractionResult
from app.models.verification import (
    PropertyVerificationRequest,
    PropertyVerificationResponse,
    VerificationStatus,
    VerificationSummary,
    VerifiedField,
    VerifiedPropertySnapshot,
)

FIELD_MAPPING = {
    "full_address": "address.full_address",
    "asking_price": "asking_price",
    "bedrooms": "bedrooms",
    "bathrooms": "bathrooms",
    "square_feet": "square_feet",
    "lot_square_feet": "lot_square_feet",
    "year_built": "year_built",
    "annual_property_tax": "annual_property_tax",
    "annual_hoa": "annual_hoa",
    "property_type": "property_type",
}

FIELD_TYPES: dict[str, type[Any]] = {
    "full_address": str,
    "asking_price": Decimal,
    "bedrooms": Decimal,
    "bathrooms": Decimal,
    "square_feet": int,
    "lot_square_feet": int,
    "year_built": int,
    "annual_property_tax": Decimal,
    "annual_hoa": Decimal,
    "property_type": str,
}


class PropertyVerificationService:
    """Builds verified field records from extraction results and user corrections."""

    def verify(self, request: PropertyVerificationRequest) -> PropertyVerificationResponse:
        extraction = request.extraction
        snapshot = VerifiedPropertySnapshot(
            source_url=extraction.source_url,
            provider=extraction.provider,
        )

        for output_field, provenance_key in FIELD_MAPPING.items():
            extracted = extraction.field_provenance.get(provenance_key) or self._fallback_field(
                extraction,
                provenance_key,
            )
            setattr(
                snapshot,
                output_field,
                self._build_field(
                    field_name=output_field,
                    extracted=extracted,
                    corrections=request.corrections,
                    confirmed_fields=request.confirmed_fields,
                ),
            )

        summary = self._summary(snapshot)
        return PropertyVerificationResponse(
            success=True,
            property=snapshot,
            verification_summary=summary,
        )

    def _build_field(
        self,
        *,
        field_name: str,
        extracted: ExtractedField[Any] | None,
        corrections: dict[str, Any],
        confirmed_fields: list[str],
    ) -> VerifiedField[Any]:
        extracted_value = None if extracted is None else extracted.value
        source = None if extracted is None else extracted.source
        confidence = None if extracted is None else Decimal(str(extracted.confidence))
        if field_name in corrections:
            final_value = self._coerce_correction(field_name, corrections[field_name])
            return VerifiedField[Any](
                extracted_value=extracted_value,
                final_value=final_value,
                status=VerificationStatus.CORRECTED,
                source=source,
                confidence=confidence,
                user_modified=True,
            )
        if field_name in confirmed_fields and extracted_value is not None:
            return VerifiedField[Any](
                extracted_value=extracted_value,
                final_value=extracted_value,
                status=VerificationStatus.VERIFIED,
                source=source,
                confidence=confidence,
                user_modified=False,
            )
        if extracted_value is None:
            return VerifiedField[Any](
                extracted_value=None,
                final_value=None,
                status=VerificationStatus.MISSING,
                source=source,
                confidence=confidence,
                user_modified=False,
            )
        return VerifiedField[Any](
            extracted_value=extracted_value,
            final_value=extracted_value,
            status=VerificationStatus.UNVERIFIED,
            source=source,
            confidence=confidence,
            user_modified=False,
        )

    def _coerce_correction(self, field_name: str, value: Any) -> Any:
        target_type = FIELD_TYPES[field_name]
        if value is None:
            return None
        if target_type is Decimal:
            return Decimal(str(value))
        if target_type is int:
            return int(value)
        if target_type is str:
            return str(value)
        return value

    def _fallback_field(
        self,
        extraction: PropertyExtractionResult,
        field_path: str,
    ) -> ExtractedField[Any] | None:
        value = self._resolve_property_path(extraction.property, field_path)
        if value is None:
            return None
        return ExtractedField[Any](
            value=value,
            source=extraction.metadata.extraction_method,
            confidence=0.5,
            raw_value=str(value),
        )

    def _resolve_property_path(self, obj: Any, field_path: str) -> Any:
        current = obj
        for part in field_path.split("."):
            current = getattr(current, part, None)
            if current is None:
                return None
        return current

    def _summary(self, snapshot: VerifiedPropertySnapshot) -> VerificationSummary:
        summary = VerificationSummary()
        for field_name in FIELD_MAPPING:
            field = getattr(snapshot, field_name)
            target = f"{field.status.value}_fields"
            if hasattr(summary, target):
                getattr(summary, target).append(field_name)
        return summary
