"""API routes for deterministic research services."""

import time

from fastapi import APIRouter, Depends, Request, status

from app.logging import logger
from app.models.public_records import (
    PublicRecordsResearchRequest,
    PublicRecordsResearchResponse,
)
from app.services.public_records_service import PublicRecordsService

router = APIRouter()


def get_public_records_service() -> PublicRecordsService:
    return PublicRecordsService()


public_records_service_dependency = Depends(get_public_records_service)


@router.post(
    "/api/v1/research/public-records",
    response_model=PublicRecordsResearchResponse,
    status_code=status.HTTP_200_OK,
)
async def research_public_records(
    request: Request,
    payload: PublicRecordsResearchRequest,
    service: PublicRecordsService = public_records_service_dependency,
) -> PublicRecordsResearchResponse:
    started_at = time.perf_counter()
    response = await service.research(payload)
    logger.info(
        "public_records_completed request_id=%s provider=%s cache_status=%s "
        "warning_count=%s duration_ms=%s",
        getattr(request.state, "request_id", "unknown"),
        None if response.result is None else response.result.provider,
        None if response.result is None else response.result.metadata.cache_status,
        0 if response.result is None else len(response.result.metadata.warnings),
        int((time.perf_counter() - started_at) * 1000),
    )
    return response
