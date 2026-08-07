"""Frontend-oriented property persistence routes."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.db.analysis_persistence import deserialize_property_record
from app.db.models import AnalysisRecord, PropertyRecord
from app.db.repositories import AnalysisRepository, PropertyRepository
from app.db.session import get_db_session
from app.logging import logger
from app.models.property_api import (
    AnalysisSummaryResponse,
    PropertyCreateRequest,
    PropertyCreateResponse,
    PropertyDetail,
    PropertyResponse,
    PropertySummaryResponse,
    PropertyUpdateRequest,
)
from app.services.property_service import PropertyService

router = APIRouter()
db_session_dependency = Depends(get_db_session)


def get_property_service(session: Session = db_session_dependency) -> PropertyService:
    return PropertyService(PropertyRepository(session))


def get_analysis_repository(session: Session = db_session_dependency) -> AnalysisRepository:
    return AnalysisRepository(session)


property_service_dependency = Depends(get_property_service)
analysis_repository_dependency = Depends(get_analysis_repository)


@router.post(
    "/api/v1/properties",
    response_model=PropertyCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_property(
    request: Request,
    payload: PropertyCreateRequest,
    property_service: PropertyService = property_service_dependency,
) -> PropertyCreateResponse:
    started_at = time.perf_counter()
    property_record = property_service.create_property(
        normalized_property=payload.property,
        verified_property=payload.verified_property,
    )
    logger.info(
        "property_create_completed request_id=%s property_id=%s duration_ms=%s",
        getattr(request.state, "request_id", "unknown"),
        property_record.id,
        int((time.perf_counter() - started_at) * 1000),
    )
    return PropertyCreateResponse(
        success=True,
        property=_property_summary_response(property_record),
    )


@router.get(
    "/api/v1/properties/{property_id}",
    response_model=PropertyResponse,
    status_code=status.HTTP_200_OK,
)
async def get_property(
    request: Request,
    property_id: str,
    property_service: PropertyService = property_service_dependency,
    analysis_repository: AnalysisRepository = analysis_repository_dependency,
) -> PropertyResponse:
    started_at = time.perf_counter()
    property_record = property_service.get_property(property_id)
    response = PropertyResponse(
        success=True,
        property=_build_property_detail(property_record, analysis_repository),
    )
    logger.info(
        "property_get_completed request_id=%s property_id=%s analysis_count=%s duration_ms=%s",
        getattr(request.state, "request_id", "unknown"),
        property_id,
        response.property.analysis_count,
        int((time.perf_counter() - started_at) * 1000),
    )
    return response


@router.patch(
    "/api/v1/properties/{property_id}",
    response_model=PropertyResponse,
    status_code=status.HTTP_200_OK,
)
async def patch_property(
    request: Request,
    property_id: str,
    payload: PropertyUpdateRequest,
    property_service: PropertyService = property_service_dependency,
    analysis_repository: AnalysisRepository = analysis_repository_dependency,
) -> PropertyResponse:
    started_at = time.perf_counter()
    property_record = property_service.update_property(
        property_id,
        normalized_property=payload.property,
        verified_property=payload.verified_property,
        current_version=payload.current_version,
    )
    response = PropertyResponse(
        success=True,
        property=_build_property_detail(property_record, analysis_repository),
    )
    logger.info(
        "property_patch_completed request_id=%s property_id=%s analysis_count=%s duration_ms=%s",
        getattr(request.state, "request_id", "unknown"),
        property_id,
        response.property.analysis_count,
        int((time.perf_counter() - started_at) * 1000),
    )
    return response


def _property_summary_response(property_record: PropertyRecord) -> PropertySummaryResponse:
    return PropertySummaryResponse(
        id=property_record.id,
        source_url=property_record.source_url,
        provider=property_record.provider,
        full_address=property_record.full_address,
        created_at=property_record.created_at,
        updated_at=property_record.updated_at,
        current_version=property_record.current_version,
    )


def _analysis_summary_response(analysis: AnalysisRecord) -> AnalysisSummaryResponse:
    return AnalysisSummaryResponse(
        id=analysis.id,
        version=analysis.version,
        status=analysis.status,
        current_stage=analysis.current_stage,
        parent_analysis_id=analysis.parent_analysis_id,
        created_at=analysis.created_at,
        completed_at=analysis.completed_at,
        failed_at=analysis.failed_at,
    )


def _build_property_detail(
    property_record: PropertyRecord,
    analysis_repository: AnalysisRepository,
) -> PropertyDetail:
    normalized_property, verified_property = deserialize_property_record(property_record)
    latest_analysis = analysis_repository.get_latest_for_property(property_record.id)
    return PropertyDetail(
        id=property_record.id,
        source_url=property_record.source_url,
        provider=property_record.provider,
        full_address=property_record.full_address,
        created_at=property_record.created_at,
        updated_at=property_record.updated_at,
        current_version=property_record.current_version,
        property=normalized_property,
        verified_property=verified_property,
        analysis_count=analysis_repository.count_for_property(property_record.id),
        latest_analysis=(
            None if latest_analysis is None else _analysis_summary_response(latest_analysis)
        ),
    )
