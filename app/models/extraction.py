"""Extraction-specific models and API schemas."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal, TypeVar

from pydantic import BaseModel, Field, HttpUrl

from app.models.property import NormalizedProperty

T = TypeVar("T")


class ExtractedField[T](BaseModel):
    """Field-level provenance captured during extraction."""

    value: T | None
    source: str
    confidence: float
    raw_value: str | None = None


class ExtractionMetadata(BaseModel):
    """Shared metadata about a provider extraction run."""

    extraction_method: str
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    fields_found: int
    fields_missing: list[str]
    warnings: list[str] = Field(default_factory=list)


class PropertyExtractionResult(BaseModel):
    """Internal provider extraction result."""

    provider: str
    source_url: str
    property: NormalizedProperty
    metadata: ExtractionMetadata
    field_provenance: dict[str, ExtractedField[Any]] = Field(default_factory=dict)


class ExtractListingRequest(BaseModel):
    """Input payload for a listing extraction request."""

    url: HttpUrl


class ErrorDetail(BaseModel):
    """Structured API error."""

    code: str
    message: str
    retryable: bool = False


class ExtractListingResponse(BaseModel):
    """Success or failure response for the extract endpoint."""

    success: bool
    provider: str | None = None
    source_url: str | None = None
    property: NormalizedProperty | None = None
    metadata: ExtractionMetadata | None = None
    error: ErrorDetail | None = None


FetchMethod = Literal["http", "playwright"]


class FetchedPage(BaseModel):
    """Fetched page content returned by the page-fetching layer."""

    requested_url: str
    final_url: str
    status_code: int
    html: str
    fetch_method: FetchMethod
    warnings: list[str] = Field(default_factory=list)
