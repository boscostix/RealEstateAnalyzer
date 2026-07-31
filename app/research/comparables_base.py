"""Provider interfaces for deterministic comparable-property services."""

from __future__ import annotations

from abc import abstractmethod

from app.models.comparables import (
    RentalCompsProviderData,
    SalesCompsProviderData,
)
from app.models.research import ResearchDomain, ResearchResult
from app.models.verification import VerifiedPropertySnapshot
from app.research.base import ResearchProvider


class SalesCompsProvider(ResearchProvider):
    """Research provider contract for sales comparable candidates."""

    domain = ResearchDomain.SALES_COMPS

    @abstractmethod
    def supports(self, property_snapshot: VerifiedPropertySnapshot) -> bool:
        """Return True when this provider can supply sales comparables."""

    @abstractmethod
    async def research(
        self,
        property_snapshot: VerifiedPropertySnapshot,
    ) -> ResearchResult[SalesCompsProviderData]:
        """Return normalized sales comparable candidates."""


class RentalCompsProvider(ResearchProvider):
    """Research provider contract for rental comparable candidates."""

    domain = ResearchDomain.RENTAL_COMPS

    @abstractmethod
    def supports(self, property_snapshot: VerifiedPropertySnapshot) -> bool:
        """Return True when this provider can supply rental comparables."""

    @abstractmethod
    async def research(
        self,
        property_snapshot: VerifiedPropertySnapshot,
    ) -> ResearchResult[RentalCompsProviderData]:
        """Return normalized rental comparable candidates."""
