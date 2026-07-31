"""Provider interface for deterministic public-records services."""

from __future__ import annotations

from abc import abstractmethod

from app.models.public_records import PublicRecordsData
from app.models.research import ResearchDomain, ResearchResult
from app.models.verification import VerifiedPropertySnapshot
from app.research.base import ResearchProvider


class PublicRecordsProvider(ResearchProvider):
    """Research provider contract for public-records services."""

    domain = ResearchDomain.PUBLIC_RECORDS

    @abstractmethod
    def supports(self, property_snapshot: VerifiedPropertySnapshot) -> bool:
        """Return True when this provider can serve the property."""

    @abstractmethod
    async def research(
        self,
        property_snapshot: VerifiedPropertySnapshot,
    ) -> ResearchResult[PublicRecordsData]:
        """Return normalized public-records data."""
