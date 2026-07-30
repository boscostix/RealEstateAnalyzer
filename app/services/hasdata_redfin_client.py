"""HasData Redfin Property API client."""

from __future__ import annotations

import httpx

from app.exceptions import FetchFailureError, ParsingFailureError
from app.services.hasdata_zillow_client import (
    HasDataZillowClientConfig,
    _BorrowedClientContext,
    _ClientContext,
    _OwnedClientContext,
    _resolve_api_key,
)


class HasDataRedfinClient:
    """Client for HasData's synchronous Redfin Property API."""

    def __init__(
        self,
        *,
        config: HasDataZillowClientConfig | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._config = config or HasDataZillowClientConfig(api_key=_resolve_api_key())
        self._client = client

    @property
    def is_configured(self) -> bool:
        return bool(self._config.api_key)

    async def fetch_property(self, url: str) -> dict[str, object]:
        """Fetch a Redfin property payload from HasData."""

        if not self.is_configured:
            raise FetchFailureError(
                message="HASDATA_API_KEY is not configured for Redfin API access.",
                retryable=False,
            )

        async with self._get_client() as client:
            try:
                response = await client.get(
                    "/scrape/redfin/property",
                    params={"url": url},
                    headers={"x-api-key": self._config.api_key or ""},
                )
            except httpx.TimeoutException as exc:
                raise FetchFailureError(
                    message="Timed out while retrieving Redfin property data from HasData.",
                    retryable=True,
                ) from exc
            except httpx.HTTPError as exc:
                raise FetchFailureError(
                    message="Failed to retrieve Redfin property data from HasData.",
                    retryable=True,
                ) from exc

        if response.status_code == 401:
            raise FetchFailureError(
                message="HasData rejected the Redfin API key.",
                retryable=False,
            )
        if response.status_code == 402:
            raise FetchFailureError(
                message="HasData credits are exhausted for the Redfin Property API.",
                retryable=False,
            )
        if response.status_code == 429:
            raise FetchFailureError(
                message="HasData rate-limited the Redfin Property API request.",
                retryable=True,
            )
        if response.status_code >= 400:
            raise FetchFailureError(
                message=(
                    f"HasData returned HTTP {response.status_code} for the Redfin "
                    "Property API request."
                ),
                retryable=response.status_code >= 500,
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise ParsingFailureError(
                message="HasData returned an invalid JSON payload for the Redfin Property API."
            ) from exc

        if not isinstance(payload, dict):
            raise ParsingFailureError(
                message="HasData returned an unexpected Redfin Property API payload."
            )
        return payload

    def _get_client(self) -> _ClientContext:
        if self._client is not None:
            return _BorrowedClientContext(self._client)
        return _OwnedClientContext(
            httpx.AsyncClient(
                base_url=self._config.base_url,
                timeout=httpx.Timeout(self._config.timeout_seconds),
                headers={"Content-Type": "application/json"},
            )
        )
