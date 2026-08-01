"""Unified non-AI research package models."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from app.models.comparables import RentalCompsData, SalesCompsData
from app.models.neighborhood import NeighborhoodData
from app.models.public_records import PublicRecordsData
from app.models.research import Citation, ResearchResult
from app.models.verification import VerifiedPropertySnapshot


class ResearchWarning(BaseModel):
    """Structured warning emitted by the research orchestrator."""

    code: str
    domain: str
    message: str
    retryable: bool = False


class ResearchPackageMetadata(BaseModel):
    """Metadata describing one orchestrated research run."""

    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    total_duration_ms: int
    completed_domains: list[str] = Field(default_factory=list)
    failed_domains: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)


class ResearchPackage(BaseModel):
    """All deterministic research sections assembled into one object."""

    property: VerifiedPropertySnapshot
    public_records: ResearchResult[PublicRecordsData] | None = None
    sales_comps: ResearchResult[SalesCompsData] | None = None
    rental_comps: ResearchResult[RentalCompsData] | None = None
    neighborhood: ResearchResult[NeighborhoodData] | None = None
    metadata: ResearchPackageMetadata
    warnings: list[ResearchWarning] = Field(default_factory=list)


class ResearchPackageRequest(BaseModel):
    """API request for the research orchestrator."""

    property: VerifiedPropertySnapshot
    bypass_cache: bool = False


class ResearchPackageResponse(BaseModel):
    """API response wrapper for orchestrated deterministic research."""

    success: bool
    package: ResearchPackage | None = None
