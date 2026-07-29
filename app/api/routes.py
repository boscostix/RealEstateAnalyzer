"""API routes for listing extraction."""

from collections.abc import Awaitable, Callable
from typing import cast

from fastapi import APIRouter, FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.exceptions import AppError, UnsupportedProviderError
from app.models.extraction import (
    ErrorDetail,
    ExtractionMetadata,
    ExtractListingRequest,
    ExtractListingResponse,
)
from app.models.property import NormalizedProperty
from app.services.provider_registry import ProviderRegistry
from app.utils.urls import validate_listing_url

router = APIRouter()
registry = ProviderRegistry.default()


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": ErrorDetail(
                code=exc.code,
                message=exc.message,
                retryable=exc.retryable,
            ).model_dump(mode="json"),
        },
    )


def add_exception_handlers(app: FastAPI) -> None:
    handler = cast(
        Callable[[Request, Exception], Awaitable[JSONResponse]],
        app_error_handler,
    )
    app.add_exception_handler(AppError, handler)


@router.post(
    "/api/v1/listings/extract",
    response_model=ExtractListingResponse,
    status_code=status.HTTP_200_OK,
)
async def extract_listing(request: ExtractListingRequest) -> ExtractListingResponse:
    validated_url = validate_listing_url(str(request.url))
    provider = registry.get_provider_name(validated_url)

    if provider is None:
        raise UnsupportedProviderError(message="This listing website is not currently supported.")

    return ExtractListingResponse(
        success=True,
        provider=provider,
        source_url=validated_url,
        property=NormalizedProperty(
            source_url=validated_url,
            provider=provider,
        ),
        metadata=ExtractionMetadata(
            extraction_method="pending",
            fields_found=0,
            fields_missing=[],
            warnings=["Extraction is not implemented until later phases."],
        ),
    )
