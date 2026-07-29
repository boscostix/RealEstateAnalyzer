"""Fixture-based tests for the Zillow provider."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from app.models.extraction import FetchedPage
from app.providers.zillow import ZillowProvider

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_zillow_provider_extracts_structured_listing() -> None:
    provider = ZillowProvider()
    page = FetchedPage(
        requested_url="https://www.zillow.com/homedetails/example",
        final_url="https://www.zillow.com/homedetails/example",
        status_code=200,
        html=load_fixture("zillow_listing.html"),
        fetch_method="http",
    )

    result = await provider.extract(page.requested_url, page)

    assert result.provider == "zillow"
    assert result.metadata.extraction_method == "next_data"
    assert result.property.address.full_address == "8400 Silverado Trl, McKinney, TX 75070"
    assert result.property.asking_price == Decimal("479990")
    assert result.property.bedrooms == Decimal("5")
    assert result.property.bathrooms == Decimal("3")
    assert result.property.square_feet == 3234
    assert result.property.annual_property_tax == Decimal("8702")
    assert result.property.property_type == "single_family"
    assert result.property.photos == [
        "https://example.com/zillow-front.jpg",
        "https://example.com/zillow-kitchen.jpg",
    ]
    assert result.field_provenance["asking_price"].source == "next_data"


@pytest.mark.asyncio
async def test_zillow_provider_handles_partial_visible_html_fallback() -> None:
    provider = ZillowProvider()
    page = FetchedPage(
        requested_url="https://www.zillow.com/homedetails/partial",
        final_url="https://www.zillow.com/homedetails/partial",
        status_code=200,
        html=load_fixture("zillow_partial.html"),
        fetch_method="http",
    )

    result = await provider.extract(page.requested_url, page)

    assert result.metadata.extraction_method == "visible_html"
    assert result.property.address.full_address == "123 Market St, Dallas, TX 75201"
    assert result.property.asking_price == Decimal("350000")
    assert result.property.bedrooms == Decimal("3")
    assert result.property.bathrooms == Decimal("2.5")
    assert result.property.square_feet == 1850
    assert "annual_property_tax" in result.metadata.fields_missing
    assert "insufficient_listing_data" not in result.metadata.warnings
