"""Frontend-oriented DTOs for property persistence APIs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, model_validator

from app.db.models import AnalysisStage, AnalysisStatus
from app.models.property import NormalizedProperty
from app.models.verification import VerifiedPropertySnapshot


class PropertyApiModel(BaseModel):
    """Base DTO for property persistence endpoints."""


class AnalysisSummaryResponse(PropertyApiModel):
    id: str
    version: int
    status: AnalysisStatus
    current_stage: AnalysisStage | None = None
    parent_analysis_id: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
    failed_at: datetime | None = None


class PropertyCreateRequest(PropertyApiModel):
    property: NormalizedProperty | None = None
    verified_property: VerifiedPropertySnapshot | None = None

    @model_validator(mode="after")
    def validate_payload(self) -> PropertyCreateRequest:
        if self.property is None and self.verified_property is None:
            raise ValueError("Either property or verified_property must be provided.")
        return self


class PropertyUpdateRequest(PropertyApiModel):
    property: NormalizedProperty | None = None
    verified_property: VerifiedPropertySnapshot | None = None
    current_version: int | None = None

    @model_validator(mode="after")
    def validate_payload(self) -> PropertyUpdateRequest:
        if (
            self.property is None
            and self.verified_property is None
            and self.current_version is None
        ):
            raise ValueError(
                "At least one of property, verified_property, or current_version must be provided."
            )
        return self


class PropertySummaryResponse(PropertyApiModel):
    id: str
    source_url: str
    provider: str
    full_address: str | None = None
    created_at: datetime
    updated_at: datetime
    current_version: int


class PropertyDetail(PropertyApiModel):
    id: str
    source_url: str
    provider: str
    full_address: str | None = None
    created_at: datetime
    updated_at: datetime
    current_version: int
    property: NormalizedProperty | None = None
    verified_property: VerifiedPropertySnapshot | None = None
    analysis_count: int
    latest_analysis: AnalysisSummaryResponse | None = None


class PropertyResponse(PropertyApiModel):
    success: bool
    property: PropertyDetail


class PropertyCreateResponse(PropertyApiModel):
    success: bool
    property: PropertySummaryResponse
