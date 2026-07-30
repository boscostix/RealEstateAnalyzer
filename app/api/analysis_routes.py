"""API routes for property verification and underwriting analysis."""

import time

from fastapi import APIRouter, Request, status

from app.exceptions import AppError
from app.logging import logger
from app.models.assumptions import RunAnalysisRequest
from app.models.underwriting import RunAnalysisResponse
from app.models.verification import PropertyVerificationRequest, PropertyVerificationResponse
from app.services.property_verification_service import PropertyVerificationService
from app.services.underwriting_service import UnderwritingService

router = APIRouter()
verification_service = PropertyVerificationService()
underwriting_service = UnderwritingService()


@router.post(
    "/api/v1/properties/verify",
    response_model=PropertyVerificationResponse,
    status_code=status.HTTP_200_OK,
)
async def verify_property(
    request: Request,
    payload: PropertyVerificationRequest,
) -> PropertyVerificationResponse:
    started_at = time.perf_counter()
    response = verification_service.verify(payload)
    verified_count = (
        len(response.verification_summary.verified_fields)
        if response.verification_summary
        else 0
    )
    corrected_count = (
        len(response.verification_summary.corrected_fields)
        if response.verification_summary
        else 0
    )
    logger.info(
        "property_verify_completed request_id=%s verified_count=%s "
        "corrected_count=%s duration_ms=%s",
        getattr(request.state, "request_id", "unknown"),
        verified_count,
        corrected_count,
        int((time.perf_counter() - started_at) * 1000),
    )
    return response


@router.post(
    "/api/v1/analyses/run",
    response_model=RunAnalysisResponse,
    status_code=status.HTTP_200_OK,
)
async def run_analysis(request: Request, payload: RunAnalysisRequest) -> RunAnalysisResponse:
    started_at = time.perf_counter()
    try:
        response = underwriting_service.run(payload)
    except AppError as exc:
        logger.warning(
            "analysis_run_failed request_id=%s preset=%s financing_type=%s "
            "error_code=%s duration_ms=%s",
            getattr(request.state, "request_id", "unknown"),
            payload.assumptions.preset,
            payload.assumptions.financing.type,
            exc.code,
            int((time.perf_counter() - started_at) * 1000),
        )
        raise
    warning_count = 0 if response.analysis is None else len(response.analysis.warnings)
    logger.info(
        "analysis_run_completed request_id=%s preset=%s financing_type=%s calculation_version=%s "
        "scenario_count=%s stress_test_count=%s warning_count=%s duration_ms=%s",
        getattr(request.state, "request_id", "unknown"),
        payload.assumptions.preset,
        payload.assumptions.financing.type,
        None if response.metadata is None else response.metadata.calculation_version,
        0 if response.analysis is None else len(response.analysis.scenarios),
        0 if response.analysis is None else len(response.analysis.stress_tests),
        warning_count,
        int((time.perf_counter() - started_at) * 1000),
    )
    return response
