"""Shared helpers for provider adapters."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.models.extraction import ExtractedField, ExtractionMetadata, PropertyExtractionResult
from app.models.property import Address, NormalizedProperty, PriceHistoryEvent, SaleHistoryEvent
from app.utils.parsing import parse_date

TrackedField = ExtractedField[Any]

SCALAR_FIELDS = (
    "listing_id",
    "latitude",
    "longitude",
    "listing_status",
    "asking_price",
    "original_listing_price",
    "days_on_market",
    "listing_date",
    "last_updated_date",
    "property_type",
    "mls_number",
    "listing_agent",
    "listing_brokerage",
    "bedrooms",
    "bathrooms",
    "square_feet",
    "lot_square_feet",
    "year_built",
    "stories",
    "garage_spaces",
    "parking_description",
    "foundation_type",
    "roof_type",
    "heating",
    "cooling",
    "exterior_material",
    "annual_property_tax",
    "annual_hoa",
    "price_per_square_foot",
    "estimated_monthly_rent",
    "estimated_property_value",
    "description",
)

ADDRESS_FIELDS = (
    "street",
    "city",
    "state",
    "postal_code",
    "full_address",
)

COLLECTION_FIELDS = (
    "features",
    "appliances",
    "school_names",
    "photos",
    "price_history",
    "sale_history",
)

MINIMUM_REQUIRED_FIELDS = (
    "address.full_address",
    "asking_price",
    "bedrooms",
    "bathrooms",
    "square_feet",
)


def record_field(
    store: dict[str, TrackedField],
    field_name: str,
    value: Any,
    *,
    source: str,
    confidence: float,
    raw_value: str | None = None,
) -> None:
    """Record a field only if it has not been filled yet and has a usable value."""

    if field_name in store or value is None:
        return
    if isinstance(value, str) and not value.strip():
        return
    if isinstance(value, list) and not value:
        return
    store[field_name] = ExtractedField[Any](
        value=value,
        source=source,
        confidence=confidence,
        raw_value=raw_value,
    )


def build_result(
    *,
    provider: str,
    source_url: str,
    field_values: Mapping[str, TrackedField],
    extraction_method: str,
    warnings: list[str] | None = None,
) -> PropertyExtractionResult:
    """Build a normalized extraction result from recorded field values."""

    property_payload = NormalizedProperty(
        source_url=source_url,
        provider=provider,
        listing_id=_field_value(field_values, "listing_id"),
        address=Address(
            street=_field_value(field_values, "address.street"),
            city=_field_value(field_values, "address.city"),
            state=_field_value(field_values, "address.state"),
            postal_code=_field_value(field_values, "address.postal_code"),
            full_address=_field_value(field_values, "address.full_address"),
        ),
        latitude=_field_value(field_values, "latitude"),
        longitude=_field_value(field_values, "longitude"),
        listing_status=_field_value(field_values, "listing_status"),
        asking_price=_field_value(field_values, "asking_price"),
        original_listing_price=_field_value(field_values, "original_listing_price"),
        days_on_market=_field_value(field_values, "days_on_market"),
        listing_date=_field_value(field_values, "listing_date"),
        last_updated_date=_field_value(field_values, "last_updated_date"),
        property_type=_field_value(field_values, "property_type"),
        mls_number=_field_value(field_values, "mls_number"),
        listing_agent=_field_value(field_values, "listing_agent"),
        listing_brokerage=_field_value(field_values, "listing_brokerage"),
        bedrooms=_field_value(field_values, "bedrooms"),
        bathrooms=_field_value(field_values, "bathrooms"),
        square_feet=_field_value(field_values, "square_feet"),
        lot_square_feet=_field_value(field_values, "lot_square_feet"),
        year_built=_field_value(field_values, "year_built"),
        stories=_field_value(field_values, "stories"),
        garage_spaces=_field_value(field_values, "garage_spaces"),
        parking_description=_field_value(field_values, "parking_description"),
        foundation_type=_field_value(field_values, "foundation_type"),
        roof_type=_field_value(field_values, "roof_type"),
        heating=_field_value(field_values, "heating"),
        cooling=_field_value(field_values, "cooling"),
        exterior_material=_field_value(field_values, "exterior_material"),
        annual_property_tax=_field_value(field_values, "annual_property_tax"),
        annual_hoa=_field_value(field_values, "annual_hoa"),
        price_per_square_foot=_field_value(field_values, "price_per_square_foot"),
        estimated_monthly_rent=_field_value(field_values, "estimated_monthly_rent"),
        estimated_property_value=_field_value(field_values, "estimated_property_value"),
        description=_field_value(field_values, "description"),
        features=_field_value(field_values, "features") or [],
        appliances=_field_value(field_values, "appliances") or [],
        school_names=_field_value(field_values, "school_names") or [],
        photos=_field_value(field_values, "photos") or [],
        price_history=_field_value(field_values, "price_history") or [],
        sale_history=_field_value(field_values, "sale_history") or [],
    )

    metadata_warnings = list(warnings or [])
    if _minimum_required_count(field_values) < 4:
        metadata_warnings.append("insufficient_listing_data")

    return PropertyExtractionResult(
        provider=provider,
        source_url=source_url,
        property=property_payload,
        metadata=ExtractionMetadata(
            extraction_method=extraction_method,
            fields_found=len(field_values),
            fields_missing=missing_fields(property_payload),
            warnings=metadata_warnings,
        ),
        field_provenance=dict(field_values),
    )


def missing_fields(property_payload: NormalizedProperty) -> list[str]:
    """Return explicit missing normalized fields for manual fallback workflows."""

    missing: list[str] = []
    for field_name in ADDRESS_FIELDS:
        if getattr(property_payload.address, field_name) is None:
            missing.append(f"address.{field_name}")
    for field_name in SCALAR_FIELDS:
        if getattr(property_payload, field_name) is None:
            missing.append(field_name)
    for field_name in COLLECTION_FIELDS:
        if not getattr(property_payload, field_name):
            missing.append(field_name)
    return missing


def price_history_events(items: object, source: str) -> list[PriceHistoryEvent]:
    """Normalize provider price history payloads."""

    if not isinstance(items, list):
        return []
    events: list[PriceHistoryEvent] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        event_name = item.get("event") or item.get("status")
        if not isinstance(event_name, str) or not event_name.strip():
            continue
        events.append(
            PriceHistoryEvent(
                date=parse_date(item.get("date")),
                event=event_name.strip(),
                price=item.get("price"),
                price_change=item.get("priceChange"),
                source=source,
            )
        )
    return events


def sale_history_events(items: object, source: str) -> list[SaleHistoryEvent]:
    """Normalize provider sale history payloads."""

    if not isinstance(items, list):
        return []
    events: list[SaleHistoryEvent] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        event_name = item.get("event") or item.get("status") or "Sale"
        events.append(
            SaleHistoryEvent(
                date=parse_date(item.get("date")),
                event=str(event_name),
                price=item.get("price"),
                source=source,
            )
        )
    return events


def _field_value(field_values: Mapping[str, TrackedField], field_name: str) -> Any:
    tracked = field_values.get(field_name)
    return None if tracked is None else tracked.value


def _minimum_required_count(field_values: Mapping[str, TrackedField]) -> int:
    return sum(1 for field_name in MINIMUM_REQUIRED_FIELDS if field_name in field_values)
