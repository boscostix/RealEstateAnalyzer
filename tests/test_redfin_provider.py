"""Fixture-based tests for the Redfin provider."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from app.models.extraction import FetchedPage
from app.providers.redfin import RedfinProvider

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
