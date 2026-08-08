"""API integration tests for the listing extraction endpoint."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from fastapi.testclient import TestClient

from app.api.routes import get_listing_service
from app.exceptions import AccessBlockedError
from app.main import app
from app.models.extraction import FetchedPage, FetchMethod
from app.providers.zillow import ZillowProvider
from app.services.hasdata_zillow_client import HasDataZillowClient
from app.services.listing_service import ListingService
from app.services.page_fetcher import PageFetcher, PlaywrightPageFetcher
from app.services.provider_registry import ProviderRegistry

FIXTURES = Path(__file__).parent / "fixtures"
client = TestClient(app)
non_raising_client = TestClient(app, raise_server_exceptions=False)


def load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class FixtureFetcher:
    def __init__(
        self,
        html: str,
        *,
        final_url: str,
        fetch_method: FetchMethod = "http",
    ) -> None:
        self._html = html
        self._final_url = final_url
        self._fetch_method = fetch_method

    async def fetch(self, url: str) -> FetchedPage:
        return FetchedPage(
            requested_url=url,
            final_url=self._final_url,
            status_code=200,
            html=self._html,
            fetch_method=self._fetch_method,
            warnings=[],
        )


class BlockedFetcher:
    async def fetch(self, url: str) -> FetchedPage:
        del url
        raise AccessBlockedError()


class BrokenService:
    async def extract(self, url: str) -> object:
        raise RuntimeError("boom")


class DisabledHasDataClient:
    @property
    def is_configured(self) -> bool:
        return False


def build_test_registry() -> ProviderRegistry:
    return ProviderRegistry(
        [ZillowProvider(hasdata_client=cast(HasDataZillowClient, DisabledHasDataClient()))]
    )


def override_with_service(service: object) -> None:
    app.dependency_overrides[get_listing_service] = lambda: service


def clear_overrides() -> None:
    app.dependency_overrides.clear()


def test_extract_listing_returns_provider_for_supported_url() -> None:
    service = ListingService(
        registry=build_test_registry(),
        page_fetcher=cast(
            PageFetcher,
            FixtureFetcher(
                load_fixture("zillow_listing.html"),
                final_url="https://www.zillow.com/homedetails/example",
            ),
        ),
        playwright_fetcher=cast(
            PlaywrightPageFetcher,
            FixtureFetcher(
                load_fixture("zillow_listing.html"),
                final_url="https://www.zillow.com/homedetails/example",
                fetch_method="playwright",
            ),
        ),
    )
    override_with_service(service)

    try:
        response = client.post(
            "/api/v1/listings/extract",
            json={"url": "https://www.zillow.com/homedetails/example"},
            headers={"X-Request-ID": "req-123"},
        )
    finally:
        clear_overrides()

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["provider"] == "zillow"
    assert payload["property"]["provider"] == "zillow"
    assert payload["property"]["asking_price"] == "479990"
    assert payload["field_provenance"]["asking_price"]["source"] == "next_data"
    assert response.headers["X-Request-ID"] == "req-123"


def test_extract_listing_uses_playwright_fallback_when_http_result_is_insufficient() -> None:
    service = ListingService(
        registry=build_test_registry(),
        page_fetcher=cast(
            PageFetcher,
            FixtureFetcher(
                load_fixture("zillow_partial.html"),
                final_url="https://www.zillow.com/homedetails/example",
            ),
        ),
        playwright_fetcher=cast(
            PlaywrightPageFetcher,
            FixtureFetcher(
                load_fixture("zillow_listing.html"),
                final_url="https://www.zillow.com/homedetails/example",
                fetch_method="playwright",
            ),
        ),
    )
    override_with_service(service)

    try:
        response = non_raising_client.post(
            "/api/v1/listings/extract",
            json={"url": "https://www.zillow.com/homedetails/example"},
        )
    finally:
        clear_overrides()

    assert response.status_code == 200
    payload = response.json()
    assert payload["metadata"]["extraction_method"] == "next_data"
    assert payload["property"]["photos"] == [
        "https://example.com/zillow-front.jpg",
        "https://example.com/zillow-kitchen.jpg",
    ]


def test_extract_listing_returns_structured_error_for_unsupported_provider() -> None:
    response = client.post(
        "/api/v1/listings/extract",
        json={"url": "https://www.example.com/listing/123"},
    )

    assert response.status_code == 400
    assert response.json() == {
        "success": False,
        "error": {
            "code": "unsupported_provider",
            "message": "This listing website is not currently supported.",
            "retryable": False,
        },
    }


def test_extract_listing_rejects_ssrf_target() -> None:
    response = client.post(
        "/api/v1/listings/extract",
        json={"url": "http://127.0.0.1/listing"},
    )

    assert response.status_code == 422
    assert response.json() == {
        "success": False,
        "error": {
            "code": "invalid_url",
            "message": "The provided host is not allowed.",
            "retryable": False,
        },
    }


def test_extract_listing_returns_blocked_error() -> None:
    service = ListingService(
        registry=build_test_registry(),
        page_fetcher=cast(PageFetcher, BlockedFetcher()),
        playwright_fetcher=cast(
            PlaywrightPageFetcher,
            FixtureFetcher(
                load_fixture("zillow_listing.html"),
                final_url="https://www.zillow.com/homedetails/example",
                fetch_method="playwright",
            ),
        ),
    )
    override_with_service(service)

    try:
        response = client.post(
            "/api/v1/listings/extract",
            json={"url": "https://www.zillow.com/homedetails/example"},
        )
    finally:
        clear_overrides()

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "access_blocked"


def test_extract_listing_returns_structured_internal_error() -> None:
    override_with_service(BrokenService())

    try:
        response = non_raising_client.post(
            "/api/v1/listings/extract",
            json={"url": "https://www.zillow.com/homedetails/example"},
        )
    finally:
        clear_overrides()

    assert response.status_code == 500
    assert response.json() == {
        "success": False,
        "error": {
            "code": "internal_server_error",
            "message": "An internal server error occurred.",
            "retryable": False,
        },
    }
