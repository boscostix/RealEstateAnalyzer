"""Common interfaces for deterministic research providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.models.research import ResearchDomain, ResearchResult
from app.models.verification import VerifiedPropertySnapshot


class ResearchProvider(ABC):
    """Common contract for deterministic research providers."""

    name: str
    domain: ResearchDomain

    @abstractmethod
    def supports(self, property_snapshot: VerifiedPropertySnapshot) -> bool:
        """Return True when the provider can research the given property."""

    @abstractmethod
    async def research(
        self,
        property_snapshot: VerifiedPropertySnapshot,
    ) -> ResearchResult[Any]:
        """Return normalized research data for the given property."""
