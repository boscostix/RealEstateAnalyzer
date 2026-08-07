"""Frontend-oriented persisted analysis routes."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.db.analysis_persistence import deserialize_analysis_record
from app.db.models import AnalysisRecord
from app.db.repositories import AnalysisRepository, PropertyRepository
from app.db.session import get_db_session
from app.logging import logger
from app.models.analysis_api import (
    AnalysisCreateRequest,
    AnalysisCreateResponse,
    AnalysisDetail,
    AnalysisDetailResponse,
    AnalysisListResponse,
)
from app.models.property_api import AnalysisSummaryResponse
from app.services.analysis_execution_service import (
    AnalysisExecutionService,
    InProcessAnalysisTaskRunner,
)
from app.services.property_service import PropertyService

router = APIRouter()
db_session_dependency = Depends(get_db_session)
analysis_task_runner = InProcessAnalysisTaskRunner()


def get_property_service(session: Session = db_session_dependency) -> PropertyService:
    return PropertyService(PropertyRepository(session))


def get_analysis_repository(session: Session = db_session_dependency) -> AnalysisRepository:
    return AnalysisRepository(session)


def get_analysis_execution_service() -> AnalysisExecutionService:
    return AnalysisExecutionService(task_runner=analysis_task_runner)


property_service_dependency = Depends(get_property_service)
analysis_repository_dependency = Depends(get_analysis_repository)
analysis_execution_service_dependency = Depends(get_analysis_execution_service)


@router.post(
    "/api/v1/properties/{property_id}/analyses",
    response_model=AnalysisCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_analysis(
    request: Request,
    property_id: str,
    payload: AnalysisCreateRequest,
    property_service: PropertyService = property_service_dependency,
    analysis_repository: AnalysisRepository = analysis_repository_dependency,
    execution_service: AnalysisExecutionService = analysis_execution_service_dependency,
) -> AnalysisCreateResponse:
    started_at = time.perf_counter()
    _, verified_property = property_service.get_property_snapshots(property_id)
    if verified_property is None:
        from app.exceptions import SnapshotValidationError

        raise SnapshotValidationError(message="The property does not have a verified snapshot.")

    analysis = analysis_repository.create(
        property_id=property_id,
        property_snapshot=verified_property,
        assumptions_snapshot=payload.assumptions,
    )
    execution_metadata = {
        "inputs": {
            "decision_context": (
                None
                if payload.decision_context is None
                else payload.decision_context.model_dump(mode="json")
            )
        }
    }
    analysis_repository.update_results(
        analysis.id,
        execution_metadata=execution_metadata,
        current_stage=analysis.current_stage,
    )

    response = AnalysisCreateResponse(success=True, analysis=_analysis_summary_response(analysis))
    execution_service.start_background_analysis(
        analysis_id=analysis.id,
        request_id=getattr(request.state, "request_id", "unknown"),
    )
    logger.info(
        "analysis_create_started request_id=%s property_id=%s "
        "analysis_id=%s version=%s duration_ms=%s",
        getattr(request.state, "request_id", "unknown"),
        property_id,
        analysis.id,
        analysis.version,
        int((time.perf_counter() - started_at) * 1000),
    )
    return response


@router.get(
    "/api/v1/analyses/{analysis_id}",
    response_model=AnalysisDetailResponse,
    status_code=status.HTTP_200_OK,
)
async def get_analysis(
    request: Request,
    analysis_id: str,
    analysis_repository: AnalysisRepository = analysis_repository_dependency,
) -> AnalysisDetailResponse:
    started_at = time.perf_counter()
    analysis = analysis_repository.get_required_by_id(analysis_id)
    response = AnalysisDetailResponse(success=True, analysis=_analysis_detail_response(analysis))
    logger.info(
        "analysis_get_completed request_id=%s analysis_id=%s status=%s duration_ms=%s",
        getattr(request.state, "request_id", "unknown"),
        analysis_id,
        analysis.status.value,
        int((time.perf_counter() - started_at) * 1000),
    )
    return response


@router.get(
    "/api/v1/properties/{property_id}/analyses",
    response_model=AnalysisListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_property_analyses(
    request: Request,
    property_id: str,
    property_service: PropertyService = property_service_dependency,
    analysis_repository: AnalysisRepository = analysis_repository_dependency,
) -> AnalysisListResponse:
    started_at = time.perf_counter()
    property_service.get_property(property_id)
    analyses = analysis_repository.list_for_property(property_id)
    response = AnalysisListResponse(
        success=True,
        analyses=[_analysis_summary_response(analysis) for analysis in analyses],
    )
    logger.info(
        "analysis_list_completed request_id=%s property_id=%s analysis_count=%s duration_ms=%s",
        getattr(request.state, "request_id", "unknown"),
        property_id,
        len(response.analyses),
        int((time.perf_counter() - started_at) * 1000),
    )
    return response


def _analysis_summary_response(analysis: AnalysisRecord) -> AnalysisSummaryResponse:
    return AnalysisSummaryResponse(
        id=analysis.id,
        property_id=analysis.property_id,
        version=analysis.version,
        status=analysis.status,
        current_stage=analysis.current_stage,
        parent_analysis_id=analysis.parent_analysis_id,
        created_at=analysis.created_at,
        completed_at=analysis.completed_at,
        failed_at=analysis.failed_at,
    )


def _analysis_detail_response(analysis: AnalysisRecord) -> AnalysisDetail:
    persisted = deserialize_analysis_record(analysis)
    return AnalysisDetail(
        id=analysis.id,
        property_id=analysis.property_id,
        version=analysis.version,
        status=analysis.status.value,
        current_stage=None if analysis.current_stage is None else analysis.current_stage.value,
        parent_analysis_id=analysis.parent_analysis_id,
        created_at=analysis.created_at.isoformat(),
        started_at=None if analysis.started_at is None else analysis.started_at.isoformat(),
        completed_at=None if analysis.completed_at is None else analysis.completed_at.isoformat(),
        failed_at=None if analysis.failed_at is None else analysis.failed_at.isoformat(),
        failure_stage=None if analysis.failure_stage is None else analysis.failure_stage.value,
        error_code=analysis.error_code,
        error_message=analysis.error_message,
        property_snapshot=(
            persisted.property_snapshot if analysis.status.value == "completed" else None
        ),
        assumptions=(
            persisted.assumptions_snapshot if analysis.status.value == "completed" else None
        ),
        underwriting=(
            persisted.underwriting_result if analysis.status.value == "completed" else None
        ),
        research=persisted.research_result if analysis.status.value == "completed" else None,
        agent_research=(
            persisted.agent_research_result if analysis.status.value == "completed" else None
        ),
        investment_committee=(
            persisted.investment_committee_result if analysis.status.value == "completed" else None
        ),
        execution=persisted.execution_metadata,
    )
