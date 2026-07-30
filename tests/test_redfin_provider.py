"""Fixture-based tests for the Redfin provider."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from app.models.extraction import FetchedPage
from app.providers.redfin import RedfinProvider
from app.services.hasdata_redfin_client import HasDataRedfinClient

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_redfin_provider_extracts_embedded_json_listing() -> None:
    provider = RedfinProvider()
    page = FetchedPage(
        requested_url="https://www.redfin.com/TX/Frisco/example/home/123",
        final_url="https://www.redfin.com/TX/Frisco/example/home/123",
        status_code=200,
        html=load_fixture("redfin_listing.html"),
        fetch_method="http",
    )

    result = await provider.extract(page.requested_url, page)

    assert result.provider == "redfin"
    assert result.metadata.extraction_method == "embedded_json"
    assert result.property.address.full_address == "901 Lakeview Dr, Frisco, TX 75034"
    assert result.property.asking_price == Decimal("615000")
    assert result.property.original_listing_price == Decimal("625000")
    assert result.property.property_type == "single_family"
    assert result.property.listing_agent == "Taylor Reed"
    assert result.property.listing_brokerage == "Metroplex Homes"
    assert len(result.property.sale_history) == 1


class StubHasDataRedfinClient(HasDataRedfinClient):
    @property
    def is_configured(self) -> bool:
        return True

    async def fetch_property(self, url: str) -> dict[str, object]:
        return {
            "property": {
                "id": 32250941,
                "status": "ACTIVE",
                "price": 615000,
                "originalPrice": 625000,
                "beds": 4,
                "baths": 3,
                "sqft": 3105,
                "lotSizeSqFt": 8400,
                "yearBuilt": 2010,
                "garageSpaces": 3,
                "stories": 2,
                "propertyType": "House",
                "pricePerSqFt": 198.07,
                "annualTax": 10220,
                "annualHoa": 1200,
                "listingAgent": "Taylor Reed",
                "brokerage": "Metroplex Homes",
                "description": "Renovated home with pool and covered patio.",
                "features": ["Pool", "Covered Patio"],
                "photos": ["https://example.com/redfin-front.jpg"],
                "listDate": "2026-05-20",
                "lastUpdated": "2026-07-18",
                "priceHistory": [{"date": "2026-05-20", "event": "Listed", "price": 625000}],
                "saleHistory": [{"date": "2021-03-01", "event": "Sold", "price": 455000}],
                "address": {
                    "street": "901 Lakeview Dr",
                    "city": "Frisco",
                    "state": "TX",
                    "zip": "75034",
                },
                "geo": {"latitude": 33.15, "longitude": -96.82},
            }
        }


@pytest.mark.asyncio
async def test_redfin_provider_extracts_hasdata_payload_from_url() -> None:
    provider = RedfinProvider(hasdata_client=StubHasDataRedfinClient())

    result = await provider.extract_from_url(
        "https://www.redfin.com/TX/Frisco/example/home/123"
    )

    assert result is not None
    assert result.metadata.extraction_method == "hasdata_api"
    assert result.property.asking_price == Decimal("615000")
    assert result.property.address.full_address == "901 Lakeview Dr, Frisco, TX 75034"
    assert result.property.listing_agent == "Taylor Reed"
