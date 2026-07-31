"""API routes for deterministic research services."""

import time

from fastapi import APIRouter, Depends, Request, status

from app.logging import logger
from app.models.comparables import (
    RentalCompsResearchRequest,
    RentalCompsResearchResponse,
    SalesCompsResearchRequest,
    SalesCompsResearchResponse,
)
from app.models.neighborhood import (
    NeighborhoodResearchRequest,
    NeighborhoodResearchResponse,
)
from app.models.public_records import (
    PublicRecordsResearchRequest,
    PublicRecordsResearchResponse,
)
from app.services.neighborhood_service import NeighborhoodService
from app.services.public_records_service import PublicRecordsService
from app.services.rental_comps_service import RentalCompsService
from app.services.sales_comps_service import SalesCompsService

router = APIRouter()


def get_public_records_service() -> PublicRecordsService:
    return PublicRecordsService()


public_records_service_dependency = Depends(get_public_records_service)


def get_sales_comps_service() -> SalesCompsService:
    return SalesCompsService()


sales_comps_service_dependency = Depends(get_sales_comps_service)


def get_rental_comps_service() -> RentalCompsService:
    return RentalCompsService()


rental_comps_service_dependency = Depends(get_rental_comps_service)


def get_neighborhood_service() -> NeighborhoodService:
    return NeighborhoodService()


neighborhood_service_dependency = Depends(get_neighborhood_service)


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


@router.post(
    "/api/v1/research/sales-comps",
    response_model=SalesCompsResearchResponse,
    status_code=status.HTTP_200_OK,
)
async def research_sales_comps(
    request: Request,
    payload: SalesCompsResearchRequest,
    service: SalesCompsService = sales_comps_service_dependency,
) -> SalesCompsResearchResponse:
    started_at = time.perf_counter()
    response = await service.research(payload)
    logger.info(
        "sales_comps_completed request_id=%s provider=%s cache_status=%s "
        "comparable_count=%s duration_ms=%s",
        getattr(request.state, "request_id", "unknown"),
        None if response.result is None else response.result.provider,
        None if response.result is None else response.result.metadata.cache_status,
        0 if response.result is None else response.result.data.summary.comparable_count,
        int((time.perf_counter() - started_at) * 1000),
    )
    return response


@router.post(
    "/api/v1/research/rental-comps",
    response_model=RentalCompsResearchResponse,
    status_code=status.HTTP_200_OK,
)
async def research_rental_comps(
    request: Request,
    payload: RentalCompsResearchRequest,
    service: RentalCompsService = rental_comps_service_dependency,
) -> RentalCompsResearchResponse:
    started_at = time.perf_counter()
    response = await service.research(payload)
    logger.info(
        "rental_comps_completed request_id=%s provider=%s cache_status=%s "
        "comparable_count=%s duration_ms=%s",
        getattr(request.state, "request_id", "unknown"),
        None if response.result is None else response.result.provider,
        None if response.result is None else response.result.metadata.cache_status,
        0 if response.result is None else response.result.data.summary.comparable_count,
        int((time.perf_counter() - started_at) * 1000),
    )
    return response


@router.post(
    "/api/v1/research/neighborhood",
    response_model=NeighborhoodResearchResponse,
    status_code=status.HTTP_200_OK,
)
async def research_neighborhood(
    request: Request,
    payload: NeighborhoodResearchRequest,
    service: NeighborhoodService = neighborhood_service_dependency,
) -> NeighborhoodResearchResponse:
    started_at = time.perf_counter()
    response = await service.research(payload)
    logger.info(
        "neighborhood_completed request_id=%s provider=%s cache_status=%s "
        "warning_count=%s duration_ms=%s",
        getattr(request.state, "request_id", "unknown"),
        None if response.result is None else response.result.provider,
        None if response.result is None else response.result.metadata.cache_status,
        0 if response.result is None else len(response.result.metadata.warnings),
        int((time.perf_counter() - started_at) * 1000),
    )
    return response
