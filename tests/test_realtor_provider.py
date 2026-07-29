"""Fixture-based tests for the Realtor provider."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from app.models.extraction import FetchedPage
from app.providers.realtor import RealtorProvider

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_realtor_provider_extracts_structured_listing() -> None:
    provider = RealtorProvider()
    page = FetchedPage(
        requested_url="https://www.realtor.com/realestateandhomes-detail/example",
        final_url="https://www.realtor.com/realestateandhomes-detail/example",
        status_code=200,
        html=load_fixture("realtor_listing.html"),
        fetch_method="http",
    )

    result = await provider.extract(page.requested_url, page)

    assert result.provider == "realtor"
    assert result.metadata.extraction_method == "next_data"
    assert result.property.address.city == "Plano"
    assert result.property.asking_price == Decimal("525000")
    assert result.property.price_per_square_foot == Decimal("181.66")
    assert result.property.listing_agent == "Jordan Smith"
    assert result.property.listing_brokerage == "North Texas Realty"
    assert result.property.features == ["Granite Counters", "Wood Floors"]
    assert result.property.school_names == ["Andrews Elementary", "Rice Middle School"]
    assert len(result.property.price_history) == 2
