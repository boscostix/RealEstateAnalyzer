"""Tests for the HasData Zillow API client."""

from __future__ import annotations

import httpx
import pytest

from app.exceptions import FetchFailureError, ParsingFailureError
from app.services.hasdata_zillow_client import (
    HasDataZillowClient,
    HasDataZillowClientConfig,
)


def build_client(handler: httpx.MockTransport) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=handler,
        base_url="https://api.hasdata.com",
    )


@pytest.mark.asyncio
async def test_hasdata_zillow_client_fetches_property_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-api-key"] == "test-key"
        assert request.url.path == "/scrape/zillow/property"
        assert request.url.params["url"] == "https://www.zillow.com/homedetails/example"
        return httpx.Response(
            200,
            json={"property": {"zpid": "123"}},
            request=request,
        )

    async with build_client(httpx.MockTransport(handler)) as client:
        api_client = HasDataZillowClient(
            config=HasDataZillowClientConfig(api_key="test-key"),
            client=client,
        )
        payload = await api_client.fetch_property("https://www.zillow.com/homedetails/example")

    assert payload["property"]["zpid"] == "123"


@pytest.mark.asyncio
async def test_hasdata_zillow_client_raises_for_credit_exhaustion() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(402, json={"message": "payment required"}, request=request)

    async with build_client(httpx.MockTransport(handler)) as client:
        api_client = HasDataZillowClient(
            config=HasDataZillowClientConfig(api_key="test-key"),
            client=client,
        )
        with pytest.raises(FetchFailureError, match="credits are exhausted"):
            await api_client.fetch_property("https://www.zillow.com/homedetails/example")


@pytest.mark.asyncio
async def test_hasdata_zillow_client_raises_for_invalid_json() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not-json", request=request)

    async with build_client(httpx.MockTransport(handler)) as client:
        api_client = HasDataZillowClient(
            config=HasDataZillowClientConfig(api_key="test-key"),
            client=client,
        )
        with pytest.raises(ParsingFailureError, match="invalid JSON"):
            await api_client.fetch_property("https://www.zillow.com/homedetails/example")
