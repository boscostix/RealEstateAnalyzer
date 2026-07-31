"""Registry helpers for deterministic research providers."""

from __future__ import annotations

from app.models.research import ResearchDomain
from app.models.verification import VerifiedPropertySnapshot
from app.research.base import ResearchProvider


class ResearchProviderRegistry:
    """Stores and filters research providers by domain and property support."""

    def __init__(self, providers: list[ResearchProvider] | None = None) -> None:
        self._providers = providers or []

    def register(self, provider: ResearchProvider) -> None:
        self._providers.append(provider)

    def providers_for_domain(self, domain: ResearchDomain) -> list[ResearchProvider]:
        return [provider for provider in self._providers if provider.domain == domain]

    def supported_providers(
        self,
        domain: ResearchDomain,
        property_snapshot: VerifiedPropertySnapshot,
    ) -> list[ResearchProvider]:
        return [
            provider
            for provider in self.providers_for_domain(domain)
            if provider.supports(property_snapshot)
        ]

    def provider_names(self, domain: ResearchDomain) -> list[str]:
        return sorted(provider.name for provider in self.providers_for_domain(domain))
