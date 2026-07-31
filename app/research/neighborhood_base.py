"""Provider interface for deterministic neighborhood research services."""

from __future__ import annotations

from abc import abstractmethod

from app.models.neighborhood import NeighborhoodData
from app.models.research import ResearchDomain, ResearchResult
from app.models.verification import VerifiedPropertySnapshot
from app.research.base import ResearchProvider


class NeighborhoodProvider(ResearchProvider):
    """Research provider contract for neighborhood datasets."""

    domain = ResearchDomain.NEIGHBORHOOD

    @abstractmethod
    def supports(self, property_snapshot: VerifiedPropertySnapshot) -> bool:
        """Return True when the provider can serve the property."""

    @abstractmethod
    async def research(
        self,
        property_snapshot: VerifiedPropertySnapshot,
    ) -> ResearchResult[NeighborhoodData]:
        """Return normalized neighborhood research."""
