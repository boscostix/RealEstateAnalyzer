"""Service layer for end-to-end listing extraction."""

from __future__ import annotations

import time
from dataclasses import dataclass
from urllib.parse import urlparse

from app.exceptions import StaticContentInsufficientError, UnsupportedProviderError
from app.models.extraction import ExtractListingResponse, PropertyExtractionResult
from app.services.page_fetcher import PageFetcher, PlaywrightPageFetcher
from app.services.provider_registry import ProviderRegistry
from app.utils.urls import validate_listing_url


@dataclass(frozen=True)
class ListingServiceResult:
    """Combined extraction output plus operational metadata for logging."""

    response: ExtractListingResponse
    provider: str
    domain: str
    fetch_method: str
    fetch_duration_ms: int
    parsing_duration_ms: int
    final_url: str


class ListingService:
    """Coordinates provider detection, page fetching, fallback, and parsing."""

    def __init__(
        self,
        *,
        registry: ProviderRegistry | None = None,
        page_fetcher: PageFetcher | None = None,
        playwright_fetcher: PlaywrightPageFetcher | None = None,
    ) -> None:
        self._registry = registry or ProviderRegistry.default()
        self._page_fetcher = page_fetcher or PageFetcher()
        self._playwright_fetcher = playwright_fetcher or PlaywrightPageFetcher()

    async def extract(self, url: str) -> ListingServiceResult:
        """Extract a normalized listing payload from a supported listing URL."""

        validated_url = validate_listing_url(url)
        provider = self._registry.detect_provider(validated_url)
        if provider is None:
            raise UnsupportedProviderError(
                message="This listing website is not currently supported."
            )

        domain = urlparse(validated_url).hostname or ""
        parsing_started_at = time.perf_counter()
        direct_result = await provider.extract_from_url(validated_url)
        if direct_result is not None:
            parsing_duration_ms = int((time.perf_counter() - parsing_started_at) * 1000)
            response = _response_from_result(direct_result)
            return ListingServiceResult(
                response=response,
                provider=provider.name,
                domain=domain,
                fetch_method="api",
                fetch_duration_ms=0,
                parsing_duration_ms=parsing_duration_ms,
                final_url=validated_url,
            )

        fetch_duration_ms = 0
        fetch_method = "http"

        try:
            fetch_started_at = time.perf_counter()
            page = await self._page_fetcher.fetch(validated_url)
        except StaticContentInsufficientError:
            fetch_duration_ms += int((time.perf_counter() - fetch_started_at) * 1000)
            fetch_started_at = time.perf_counter()
            page = await self._playwright_fetcher.fetch(validated_url)
            fetch_duration_ms += int((time.perf_counter() - fetch_started_at) * 1000)
            fetch_method = "playwright"
        else:
            fetch_duration_ms += int((time.perf_counter() - fetch_started_at) * 1000)
            fetch_method = page.fetch_method

        parsing_started_at = time.perf_counter()
        result = await provider.extract(validated_url, page)
        parsing_duration_ms = int((time.perf_counter() - parsing_started_at) * 1000)

        if self._should_use_playwright(result, page.fetch_method):
            fetch_started_at = time.perf_counter()
            page = await self._playwright_fetcher.fetch(validated_url)
            fetch_duration_ms += int((time.perf_counter() - fetch_started_at) * 1000)
            parsing_started_at = time.perf_counter()
            result = await provider.extract(validated_url, page)
            parsing_duration_ms += int((time.perf_counter() - parsing_started_at) * 1000)
            fetch_method = page.fetch_method

        response = _response_from_result(result)
        return ListingServiceResult(
            response=response,
            provider=provider.name,
            domain=domain,
            fetch_method=fetch_method,
            fetch_duration_ms=fetch_duration_ms,
            parsing_duration_ms=parsing_duration_ms,
            final_url=page.final_url,
        )

    @staticmethod
    def _should_use_playwright(
        result: PropertyExtractionResult,
        fetch_method: str,
    ) -> bool:
        return fetch_method == "http" and (
            result.metadata.extraction_method == "visible_html"
            or "insufficient_listing_data" in result.metadata.warnings
        )


def _response_from_result(result: PropertyExtractionResult) -> ExtractListingResponse:
    return ExtractListingResponse(
        success=True,
        provider=result.provider,
        source_url=result.source_url,
        property=result.property,
        metadata=result.metadata,
        field_provenance=result.field_provenance,
    )
