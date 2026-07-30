"""API routes for listing extraction."""

import time
from collections.abc import Awaitable, Callable
from typing import cast

from fastapi import APIRouter, Depends, FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.exceptions import AppError, InternalApplicationError
from app.logging import logger
from app.models.extraction import ErrorDetail, ExtractListingRequest, ExtractListingResponse
from app.services.listing_service import ListingService

router = APIRouter()


def get_listing_service() -> ListingService:
    return ListingService()


listing_service_dependency = Depends(get_listing_service)


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": ErrorDetail(
                code=exc.code,
                message=exc.message,
                field=exc.field,
                retryable=exc.retryable,
            ).model_dump(mode="json", exclude_none=True),
        },
    )


async def unexpected_error_handler(_: Request, exc: Exception) -> JSONResponse:
    error = InternalApplicationError()
    logger.exception("unhandled_exception", exc_info=exc)
    return JSONResponse(
        status_code=error.status_code,
        content={
            "success": False,
            "error": ErrorDetail(
                code=error.code,
                message=error.message,
                field=error.field,
                retryable=error.retryable,
            ).model_dump(mode="json", exclude_none=True),
        },
    )


def add_exception_handlers(app: FastAPI) -> None:
    handler = cast(
        Callable[[Request, Exception], Awaitable[JSONResponse]],
        app_error_handler,
    )
    app.add_exception_handler(AppError, handler)
    app.add_exception_handler(Exception, unexpected_error_handler)


@router.post(
    "/api/v1/listings/extract",
    response_model=ExtractListingResponse,
    status_code=status.HTTP_200_OK,
)
async def extract_listing(
    request: Request,
    payload: ExtractListingRequest,
    service: ListingService = listing_service_dependency,
) -> ExtractListingResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    started_at = time.perf_counter()
    domain = payload.url.host or ""

    try:
        result = await service.extract(str(payload.url))
    except AppError as exc:
        total_duration_ms = int((time.perf_counter() - started_at) * 1000)
        logger.warning(
            "listing_extract_failed "
            "request_id=%s provider=%s domain=%s fetch_method=%s fetch_duration_ms=%s "
            "parsing_duration_ms=%s fields_found=%s warning_count=%s error_code=%s "
            "duration_ms=%s",
            request_id,
            None,
            domain,
            None,
            0,
            0,
            0,
            0,
            exc.code,
            total_duration_ms,
        )
        raise

    total_duration_ms = int((time.perf_counter() - started_at) * 1000)
    fields_found = 0 if result.response.metadata is None else result.response.metadata.fields_found
    warning_count = (
        0 if result.response.metadata is None else len(result.response.metadata.warnings)
    )
    logger.info(
        "listing_extract_completed "
        "request_id=%s provider=%s domain=%s fetch_method=%s fetch_duration_ms=%s "
        "parsing_duration_ms=%s fields_found=%s warning_count=%s error_code=%s "
        "duration_ms=%s",
        request_id,
        result.provider,
        result.domain,
        result.fetch_method,
        result.fetch_duration_ms,
        result.parsing_duration_ms,
        fields_found,
        warning_count,
        None,
        total_duration_ms,
    )
    return result.response
