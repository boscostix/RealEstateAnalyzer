"""HasData Zillow Property API client."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from app.exceptions import FetchFailureError, ParsingFailureError


@dataclass(frozen=True)
class HasDataZillowClientConfig:
    """Configuration for the HasData Zillow Property API client."""

    api_key: str | None
    base_url: str = "https://api.hasdata.com"
    timeout_seconds: float = 20.0


class HasDataZillowClient:
    """Client for HasData's synchronous Zillow Property API."""

    def __init__(
        self,
        *,
        config: HasDataZillowClientConfig | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._config = config or HasDataZillowClientConfig(
            api_key=_resolve_api_key(),
        )
        self._client = client

    @property
    def is_configured(self) -> bool:
        return bool(self._config.api_key)

    async def fetch_property(
        self,
        url: str,
        *,
        extract_agent_emails: bool = False,
    ) -> dict[str, Any]:
        """Fetch a Zillow property payload from HasData."""

        if not self.is_configured:
            raise FetchFailureError(
                message="HASDATA_API_KEY is not configured for Zillow API access.",
                retryable=False,
            )

        params: dict[str, str | bool] = {"url": url}
        if extract_agent_emails:
            params["extractAgentEmails"] = True

        async with self._get_client() as client:
            try:
                response = await client.get(
                    "/scrape/zillow/property",
                    params=params,
                    headers={"x-api-key": self._config.api_key or ""},
                )
            except httpx.TimeoutException as exc:
                raise FetchFailureError(
                    message="Timed out while retrieving Zillow property data from HasData.",
                    retryable=True,
                ) from exc
            except httpx.HTTPError as exc:
                raise FetchFailureError(
                    message="Failed to retrieve Zillow property data from HasData.",
                    retryable=True,
                ) from exc

        if response.status_code == 401:
            raise FetchFailureError(
                message="HasData rejected the Zillow API key.",
                retryable=False,
            )
        if response.status_code == 402:
            raise FetchFailureError(
                message="HasData credits are exhausted for the Zillow Property API.",
                retryable=False,
            )
        if response.status_code == 429:
            raise FetchFailureError(
                message="HasData rate-limited the Zillow Property API request.",
                retryable=True,
            )
        if response.status_code >= 400:
            raise FetchFailureError(
                message=(
                    f"HasData returned HTTP {response.status_code} for the Zillow "
                    "Property API request."
                ),
                retryable=response.status_code >= 500,
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise ParsingFailureError(
                message="HasData returned an invalid JSON payload for the Zillow Property API."
            ) from exc

        if not isinstance(payload, dict):
            raise ParsingFailureError(
                message="HasData returned an unexpected Zillow Property API payload."
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


def _resolve_api_key() -> str | None:
    env_value = os.getenv("HASDATA_API_KEY")
    if env_value:
        return env_value

    file_path = os.getenv("HASDATA_API_KEY_FILE", "secrets/hasdata_api_key.txt")
    path = Path(file_path)
    if not path.is_file():
        return None

    value = path.read_text(encoding="utf-8").strip()
    return value or None
