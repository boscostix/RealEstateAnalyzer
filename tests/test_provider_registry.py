"""Tests for provider detection."""

from app.services.provider_registry import ProviderRegistry


def test_registry_detects_zillow() -> None:
    registry = ProviderRegistry.default()

    assert registry.get_provider_name("https://www.zillow.com/homedetails/example") == "zillow"

def test_registry_detects_redfin() -> None:
    registry = ProviderRegistry.default()

    assert registry.get_provider_name("https://www.redfin.com/TX/Dallas/example/home/123") == (
        "redfin"
    )


def test_registry_returns_none_for_unsupported_provider() -> None:
    registry = ProviderRegistry.default()

    assert registry.get_provider_name("https://www.example.com/listing/123") is None
