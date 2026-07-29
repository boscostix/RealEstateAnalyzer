"""HTTP page fetcher with SSRF protections and blocked-page detection."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.exceptions import (
    AccessBlockedError,
    CaptchaDetectedError,
    FetchFailureError,
    InvalidURLError,
    ListingNotFoundError,
)
from app.models.extraction import FetchedPage
from app.utils.urls import validate_listing_url, validate_resolved_addresses

Resolver = Callable[[str], Awaitable[list[str]]]


@dataclass(frozen=True)
class FetcherConfig:
    """Configuration for the HTTP page fetcher."""

    user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    )
    connect_timeout: float = 5.0
    read_timeout: float = 10.0
    max_redirects: int = 5
    max_response_bytes: int = 2_000_000


class PageFetcher:
    """Fetches listing pages over HTTP with conservative safety controls."""

    def __init__(
        self,
        *,
        client: httpx.AsyncClient | None = None,
        resolver: Resolver | None = None,
        config: FetcherConfig | None = None,
    ) -> None:
        self._client = client
        self._resolver = resolver or default_resolver
        self._config = config or FetcherConfig()

    async def fetch(self, url: str) -> FetchedPage:
        """Fetch a listing page over HTTP while enforcing redirect and size limits."""

        validated_url = validate_listing_url(url)
        current_url = validated_url
        redirect_count = 0

        async with self._get_client() as client:
            while True:
                await self._validate_hostname(current_url)

                try:
                    response = await client.get(current_url, follow_redirects=False)
                except httpx.TimeoutException as exc:
                    raise FetchFailureError(
                        message="Timed out while retrieving the listing page.",
                        retryable=True,
                    ) from exc
                except httpx.HTTPError as exc:
                    raise FetchFailureError(
                        message="Failed to retrieve the listing page.",
                        retryable=True,
                    ) from exc

                if self._is_redirect(response):
                    if redirect_count >= self._config.max_redirects:
                        raise FetchFailureError(
                            message="Too many redirects while retrieving the listing page.",
                            retryable=False,
                        )

                    location = response.headers.get("location")
                    if not location:
                        raise FetchFailureError(
                            message="Redirect response did not include a location header.",
                            retryable=False,
                        )

                    current_url = validate_listing_url(urljoin(current_url, location))
                    redirect_count += 1
                    continue

                html = await self._read_response_body(response)
                self._raise_for_problem_response(response, html)
                self._raise_for_blocked_page(response, html)

                return FetchedPage(
                    requested_url=validated_url,
                    final_url=str(response.url),
                    status_code=response.status_code,
                    html=html,
                    fetch_method="http",
                    warnings=[],
                )

    def _get_client(self) -> _ClientContext:
        timeout = httpx.Timeout(
            connect=self._config.connect_timeout,
            read=self._config.read_timeout,
            write=self._config.read_timeout,
            pool=self._config.read_timeout,
        )
        headers = {
            "User-Agent": self._config.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        if self._client is not None:
            return _BorrowedClientContext(self._client)
        return _OwnedClientContext(
            httpx.AsyncClient(
                timeout=timeout,
                headers=headers,
                follow_redirects=False,
            )
        )

    async def _validate_hostname(self, url: str) -> None:
        hostname = urlparse(url).hostname
        if hostname is None:
            raise InvalidURLError(message="A valid absolute URL is required.")
        await validate_resolved_addresses(hostname, self._resolver)

    async def _read_response_body(self, response: httpx.Response) -> str:
        content_length = response.headers.get("content-length")
        if content_length is not None:
            try:
                declared_length = int(content_length)
            except ValueError:
                pass
            else:
                if declared_length > self._config.max_response_bytes:
                    raise FetchFailureError(
                        message="The listing page response exceeded the allowed size limit.",
                        retryable=False,
                    )

        body = await response.aread()
        if len(body) > self._config.max_response_bytes:
            raise FetchFailureError(
                message="The listing page response exceeded the allowed size limit.",
                retryable=False,
            )
        return body.decode(response.encoding or "utf-8", errors="replace")

    def _raise_for_problem_response(self, response: httpx.Response, html: str) -> None:
        if response.status_code == 404:
            raise ListingNotFoundError()
        if response.status_code in {401, 403, 429}:
            self._raise_for_blocked_page(response, html)
            raise AccessBlockedError()
        if response.status_code >= 400:
            raise FetchFailureError(
                message=(
                    f"Unexpected HTTP status {response.status_code} while "
                    "retrieving the listing page."
                ),
                retryable=response.status_code >= 500,
            )

    def _raise_for_blocked_page(self, response: httpx.Response, html: str) -> None:
        normalized_html = html.lower()
        if any(
            marker in normalized_html
            for marker in (
                "captcha",
                "verify you are human",
                "human verification",
                "bot verification",
                "recaptcha",
                "hcaptcha",
            )
        ):
            raise CaptchaDetectedError()

        if response.status_code in {401, 403, 429} or any(
            marker in normalized_html
            for marker in (
                "access denied",
                "request blocked",
                "you have been blocked",
                "temporarily unavailable",
                "cloudflare",
                "attention required",
            )
        ):
            raise AccessBlockedError()

        if _looks_like_empty_application_shell(html):
            raise AccessBlockedError(
                message=(
                    "The listing website returned an empty application shell "
                    "instead of listing content."
                )
            )

    @staticmethod
    def _is_redirect(response: httpx.Response) -> bool:
        return response.status_code in {301, 302, 303, 307, 308}


class _ClientContext:
    async def __aenter__(self) -> httpx.AsyncClient:
        raise NotImplementedError

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        raise NotImplementedError


class _OwnedClientContext(_ClientContext):
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def __aenter__(self) -> httpx.AsyncClient:
        return self._client

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        await self._client.aclose()


class _BorrowedClientContext(_ClientContext):
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def __aenter__(self) -> httpx.AsyncClient:
        return self._client

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None


async def default_resolver(hostname: str) -> list[str]:
    """Resolve a hostname to IP addresses for SSRF revalidation."""

    import asyncio

    loop = asyncio.get_running_loop()
    addrinfo = await loop.getaddrinfo(hostname, None, type=0, proto=0, flags=0)
    resolved: list[str] = []
    for entry in addrinfo:
        address = entry[4][0]
        if isinstance(address, str) and address not in resolved:
            resolved.append(address)
    return resolved


def _looks_like_empty_application_shell(html: str) -> bool:
    soup = BeautifulSoup(html, "html.parser")
    visible_text = " ".join(soup.stripped_strings).strip().lower()
    shell_markers = ("__next", 'id="root"', 'id="app"', "data-reactroot")
    has_shell_marker = any(marker in html.lower() for marker in shell_markers)
    return has_shell_marker and len(visible_text) < 50
