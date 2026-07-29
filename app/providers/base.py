"""Provider interfaces and shared helpers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.extraction import FetchedPage, PropertyExtractionResult


class ListingProvider(ABC):
    """Common interface for provider-specific extractors."""

    name: str
    supported_domains: tuple[str, ...]

    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Return True when the provider can parse the URL."""

    @abstractmethod
    async def extract(self, url: str, page: FetchedPage) -> PropertyExtractionResult:
        """Extract normalized property data from a fetched page."""
