"""Tests for the static HTTP page fetcher."""

from __future__ import annotations

import httpx
import pytest

from app.exceptions import (
    AccessBlockedError,
    CaptchaDetectedError,
    FetchFailureError,
    InvalidURLError,
    ListingNotFoundError,
    StaticContentInsufficientError,
)
from app.services.page_fetcher import FetcherConfig, PageFetcher


async def allow_public_resolution(_: str) -> list[str]:
    return ["93.184.216.34"]


def build_client(handler: httpx.MockTransport) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=handler)


@pytest.mark.asyncio
async def test_page_fetcher_returns_fetched_page_for_successful_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text="<html><body><h1>Listing</h1></body></html>",
            request=request,
        )

    async with build_client(httpx.MockTransport(handler)) as client:
        fetcher = PageFetcher(client=client, resolver=allow_public_resolution)

        page = await fetcher.fetch("https://www.zillow.com/homedetails/example")

    assert page.requested_url == "https://www.zillow.com/homedetails/example"
    assert page.final_url == "https://www.zillow.com/homedetails/example"
    assert page.status_code == 200
    assert page.fetch_method == "http"
    assert "Listing" in page.html


@pytest.mark.asyncio
async def test_page_fetcher_follows_redirects_and_revalidates_target() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == "https://www.zillow.com/homedetails/example":
            return httpx.Response(
                302,
                headers={"Location": "https://www.zillow.com/homedetails/updated"},
                request=request,
            )
        return httpx.Response(200, text="<html>updated</html>", request=request)

    async with build_client(httpx.MockTransport(handler)) as client:
        fetcher = PageFetcher(client=client, resolver=allow_public_resolution)

        page = await fetcher.fetch("https://www.zillow.com/homedetails/example")

    assert page.final_url == "https://www.zillow.com/homedetails/updated"
    assert page.html == "<html>updated</html>"


@pytest.mark.asyncio
async def test_page_fetcher_rejects_redirect_to_private_target() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            302,
            headers={"Location": "http://127.0.0.1/admin"},
            request=request,
        )

    async with build_client(httpx.MockTransport(handler)) as client:
        fetcher = PageFetcher(client=client, resolver=allow_public_resolution)

        with pytest.raises(InvalidURLError):
            await fetcher.fetch("https://www.zillow.com/homedetails/example")


@pytest.mark.asyncio
async def test_page_fetcher_rejects_private_dns_resolution() -> None:
    async def resolve_private(_: str) -> list[str]:
        return ["10.0.0.8"]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>ok</html>", request=request)

    async with build_client(httpx.MockTransport(handler)) as client:
        fetcher = PageFetcher(client=client, resolver=resolve_private)

        with pytest.raises(InvalidURLError):
            await fetcher.fetch("https://www.zillow.com/homedetails/example")


@pytest.mark.asyncio
async def test_page_fetcher_raises_for_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    async with build_client(httpx.MockTransport(handler)) as client:
        fetcher = PageFetcher(client=client, resolver=allow_public_resolution)

        with pytest.raises(FetchFailureError, match="Timed out"):
            await fetcher.fetch("https://www.zillow.com/homedetails/example")


@pytest.mark.asyncio
async def test_page_fetcher_raises_for_oversized_response() -> None:
    body = "x" * 25

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text=body,
            headers={"Content-Length": str(len(body))},
            request=request,
        )

    config = FetcherConfig(max_response_bytes=10)

    async with build_client(httpx.MockTransport(handler)) as client:
        fetcher = PageFetcher(
            client=client,
            resolver=allow_public_resolution,
            config=config,
        )

        with pytest.raises(FetchFailureError, match="size limit"):
            await fetcher.fetch("https://www.zillow.com/homedetails/example")


@pytest.mark.asyncio
async def test_page_fetcher_detects_captcha_page() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text="<html><body>Please complete the CAPTCHA challenge</body></html>",
            request=request,
        )

    async with build_client(httpx.MockTransport(handler)) as client:
        fetcher = PageFetcher(client=client, resolver=allow_public_resolution)

        with pytest.raises(CaptchaDetectedError):
            await fetcher.fetch("https://www.zillow.com/homedetails/example")


@pytest.mark.asyncio
async def test_page_fetcher_detects_access_blocked_page() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            text="<html><body>Access denied</body></html>",
            request=request,
        )

    async with build_client(httpx.MockTransport(handler)) as client:
        fetcher = PageFetcher(client=client, resolver=allow_public_resolution)

        with pytest.raises(AccessBlockedError):
            await fetcher.fetch("https://www.zillow.com/homedetails/example")


@pytest.mark.asyncio
async def test_page_fetcher_detects_empty_application_shell() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text='<html><body><div id="root"></div><script src="/app.js"></script></body></html>',
            request=request,
        )

    async with build_client(httpx.MockTransport(handler)) as client:
        fetcher = PageFetcher(client=client, resolver=allow_public_resolution)

        with pytest.raises(StaticContentInsufficientError, match="empty application shell"):
            await fetcher.fetch("https://www.zillow.com/homedetails/example")


@pytest.mark.asyncio
async def test_page_fetcher_raises_for_not_found() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="<html>not found</html>", request=request)

    async with build_client(httpx.MockTransport(handler)) as client:
        fetcher = PageFetcher(client=client, resolver=allow_public_resolution)

        with pytest.raises(ListingNotFoundError):
            await fetcher.fetch("https://www.zillow.com/homedetails/example")


@pytest.mark.asyncio
async def test_page_fetcher_raises_for_too_many_redirects() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            302,
            headers={"Location": "https://www.zillow.com/homedetails/example"},
            request=request,
        )

    config = FetcherConfig(max_redirects=1)

    async with build_client(httpx.MockTransport(handler)) as client:
        fetcher = PageFetcher(
            client=client,
            resolver=allow_public_resolution,
            config=config,
        )

        with pytest.raises(FetchFailureError, match="Too many redirects"):
            await fetcher.fetch("https://www.zillow.com/homedetails/example")
