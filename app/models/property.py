"""Normalized property data models."""

from __future__ import annotations

from datetime import date as dt_date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class Address(BaseModel):
    """Normalized address components."""

    street: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    full_address: str | None = None


class PriceHistoryEvent(BaseModel):
    """A normalized price history event."""

    date: dt_date | None = None
    event: str
    price: Decimal | None = None
    price_change: Decimal | None = None
    source: str | None = None


class SaleHistoryEvent(BaseModel):
    """A normalized sale history event."""

    date: dt_date | None = None
    event: str
    price: Decimal | None = None
    source: str | None = None


class NormalizedProperty(BaseModel):
    """Provider-agnostic property listing payload."""

    model_config = ConfigDict(populate_by_name=True)

    source_url: str
    provider: str
    listing_id: str | None = None
    address: Address = Field(default_factory=Address)
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    listing_status: str | None = None
    asking_price: Decimal | None = None
    original_listing_price: Decimal | None = None
    days_on_market: int | None = None
    listing_date: dt_date | None = None
    last_updated_date: dt_date | None = None
    property_type: str | None = None
    mls_number: str | None = None
    listing_agent: str | None = None
    listing_brokerage: str | None = None
    bedrooms: Decimal | None = None
    bathrooms: Decimal | None = None
    square_feet: int | None = None
    lot_square_feet: int | None = None
    year_built: int | None = None
    stories: Decimal | None = None
    garage_spaces: Decimal | None = None
    parking_description: str | None = None
    foundation_type: str | None = None
    roof_type: str | None = None
    heating: str | None = None
    cooling: str | None = None
    exterior_material: str | None = None
    annual_property_tax: Decimal | None = None
    annual_hoa: Decimal | None = None
    price_per_square_foot: Decimal | None = None
    estimated_monthly_rent: Decimal | None = None
    estimated_property_value: Decimal | None = None
    description: str | None = None
    features: list[str] = Field(default_factory=list)
    appliances: list[str] = Field(default_factory=list)
    school_names: list[str] = Field(default_factory=list)
    photos: list[str] = Field(default_factory=list)
    price_history: list[PriceHistoryEvent] = Field(default_factory=list)
    sale_history: list[SaleHistoryEvent] = Field(default_factory=list)
