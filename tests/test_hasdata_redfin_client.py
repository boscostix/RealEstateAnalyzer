"""Tests for the HasData Redfin API client."""

from __future__ import annotations

import httpx
import pytest

from app.exceptions import FetchFailureError, ParsingFailureError
from app.services.hasdata_redfin_client import HasDataRedfinClient
from app.services.hasdata_zillow_client import HasDataZillowClientConfig


def build_client(handler: httpx.MockTransport) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=handler,
        base_url="https://api.hasdata.com",
    )


@pytest.mark.asyncio
async def test_hasdata_redfin_client_fetches_property_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-api-key"] == "test-key"
        assert request.url.path == "/scrape/redfin/property"
        assert request.url.params["url"] == "https://www.redfin.com/TX/Frisco/example/home/123"
        return httpx.Response(
            200,
            json={"property": {"id": 123}},
            request=request,
        )

    async with build_client(httpx.MockTransport(handler)) as client:
        api_client = HasDataRedfinClient(
            config=HasDataZillowClientConfig(api_key="test-key"),
            client=client,
        )
        payload = await api_client.fetch_property(
            "https://www.redfin.com/TX/Frisco/example/home/123"
        )

    property_payload = payload["property"]
    assert isinstance(property_payload, dict)
    assert property_payload["id"] == 123


@pytest.mark.asyncio
async def test_hasdata_redfin_client_raises_for_credit_exhaustion() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(402, json={"message": "payment required"}, request=request)

    async with build_client(httpx.MockTransport(handler)) as client:
        api_client = HasDataRedfinClient(
            config=HasDataZillowClientConfig(api_key="test-key"),
            client=client,
        )
        with pytest.raises(FetchFailureError, match="credits are exhausted"):
            await api_client.fetch_property("https://www.redfin.com/TX/Frisco/example/home/123")


@pytest.mark.asyncio
async def test_hasdata_redfin_client_raises_for_invalid_json() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not-json", request=request)

    async with build_client(httpx.MockTransport(handler)) as client:
        api_client = HasDataRedfinClient(
            config=HasDataZillowClientConfig(api_key="test-key"),
            client=client,
        )
        with pytest.raises(ParsingFailureError, match="invalid JSON"):
            await api_client.fetch_property("https://www.redfin.com/TX/Frisco/example/home/123")
