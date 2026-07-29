"""Provider registry used to match listing URLs to provider adapters."""

from __future__ import annotations

from urllib.parse import urlparse

from app.providers.base import ListingProvider
from app.providers.realtor import RealtorProvider
from app.providers.redfin import RedfinProvider
from app.providers.zillow import ZillowProvider


class ProviderRegistry:
    """Resolves URLs to provider adapters."""

    def __init__(self, providers: list[ListingProvider]) -> None:
        self._providers = providers

    @classmethod
    def default(cls) -> ProviderRegistry:
        return cls(
            providers=[
                ZillowProvider(),
                RealtorProvider(),
                RedfinProvider(),
            ]
        )

    def detect_provider(self, url: str) -> ListingProvider | None:
        for provider in self._providers:
            if provider.can_handle(url):
                return provider
        return None

    def get_provider_name(self, url: str) -> str | None:
        provider = self.detect_provider(url)
        return None if provider is None else provider.name

    def supported_domains(self) -> list[str]:
        return sorted(
            {domain for provider in self._providers for domain in provider.supported_domains}
        )

    @staticmethod
    def extract_hostname(url: str) -> str:
        parsed = urlparse(url)
        return parsed.hostname or ""
