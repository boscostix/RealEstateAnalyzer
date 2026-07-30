"""Tests for listing service orchestration."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.models.extraction import PropertyExtractionResult
from app.models.property import NormalizedProperty
from app.providers.base import ListingProvider
from app.services.listing_service import ListingService
from app.services.provider_registry import ProviderRegistry


class DirectProvider(ListingProvider):
    name = "zillow"
    supported_domains = ("zillow.com", "www.zillow.com")

    def __init__(self) -> None:
        self.extract_called = False

    def can_handle(self, url: str) -> bool:
        return "zillow.com" in url

    async def extract_from_url(self, url: str) -> PropertyExtractionResult | None:
        return PropertyExtractionResult(
            provider="zillow",
            source_url=url,
            property=NormalizedProperty(
                source_url=url,
                provider="zillow",
                asking_price=Decimal("100"),
            ),
            metadata={
                "extraction_method": "hasdata_api",
                "fields_found": 1,
                "fields_missing": [],
                "warnings": [],
            },
        )

    async def extract(self, url: str, page: object) -> PropertyExtractionResult:
        self.extract_called = True
        raise AssertionError("HTML extraction should not be called when direct API succeeds.")


class FailingFetcher:
    async def fetch(self, url: str) -> object:
        raise AssertionError("Page fetcher should not be used when direct API succeeds.")


@pytest.mark.asyncio
async def test_listing_service_prefers_direct_provider_extraction() -> None:
    provider = DirectProvider()
    service = ListingService(
        registry=ProviderRegistry([provider]),
        page_fetcher=FailingFetcher(),
    )

    result = await service.extract("https://www.zillow.com/homedetails/example")

    assert result.fetch_method == "api"
    assert result.response.provider == "zillow"
    assert result.response.property is not None
    assert result.response.property.asking_price == Decimal("100")
    assert provider.extract_called is False
