"""Shared deterministic research models."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class SourceType(StrEnum):
    """Supported source categories for deterministic research."""

    API = "api"
    GOVERNMENT = "government"
    GEOSPATIAL = "geospatial"
    MARKETPLACE = "marketplace"
    DATASET = "dataset"
    INTERNAL = "internal"
    OTHER = "other"


class CacheStatus(StrEnum):
    """Whether a research response came from cache."""

    HIT = "hit"
    MISS = "miss"
    STALE = "stale"
    BYPASS = "bypass"


class ResearchDomain(StrEnum):
    """Top-level research service categories."""

    PUBLIC_RECORDS = "public_records"
    SALES_COMPS = "sales_comps"
    RENTAL_COMPS = "rental_comps"
    NEIGHBORHOOD = "neighborhood"


class ConfidenceScore(BaseModel):
    """Confidence score for either a single field or an overall result."""

    value: Decimal
    reason: str | None = None

    @field_validator("value")
    @classmethod
    def validate_value(cls, value: Decimal) -> Decimal:
        if value < 0 or value > 1:
            raise ValueError("Confidence scores must be between 0 and 1.")
        return value


class Source(BaseModel):
    """A concrete upstream source used to gather research data."""

    name: str
    type: SourceType
    url: str
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Citation(BaseModel):
    """A citation that ties returned data back to a specific source."""

    source_name: str
    source_url: str
    source_type: SourceType
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    note: str | None = None


class ResearchField[T](BaseModel):
    """Field-level deterministic research value with confidence and provenance."""

    value: T | None
    confidence: ConfidenceScore
    citations: list[Citation] = Field(default_factory=list)


class ResearchMetadata(BaseModel):
    """Operational metadata for a research provider response."""

    provider: str
    domain: ResearchDomain
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    provider_latency_ms: int
    cache_status: CacheStatus
    source_url: str | None = None
    source_name: str | None = None
    warnings: list[str] = Field(default_factory=list)

    @field_validator("provider_latency_ms")
    @classmethod
    def validate_latency(cls, value: int) -> int:
        if value < 0:
            raise ValueError("Provider latency must be non-negative.")
        return value


class ResearchResult[T](BaseModel):
    """Unified return type for deterministic research providers."""

    provider: str
    retrieved_at: datetime
    metadata: ResearchMetadata
    confidence: ConfidenceScore
    citations: list[Citation] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    data: T


class CacheEntry[T](BaseModel):
    """A cached research payload with expiry metadata."""

    key: str
    value: ResearchResult[T]
    expires_at: datetime


ResearchPayload = dict[str, ResearchField[Any] | list[Any] | dict[str, Any] | Any]
