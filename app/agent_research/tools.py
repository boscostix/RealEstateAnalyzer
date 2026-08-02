"""Typed function tools that expose approved deterministic services to agents."""

from __future__ import annotations

from typing import Annotated, Any

from agents import RunContextWrapper, function_tool
from pydantic import BaseModel, Field

from app.agent_research.context import AgentRunContext
from app.agent_research.evidence import (
    build_evidence_index,
    build_property_key,
    citation_ids_for_source_ids,
    source_ids_for_label,
)
from app.agent_research.exceptions import MissingAgentInputError
from app.agent_research.sanitization import sanitize_for_agent
from app.agent_research.tool_models import (
    FloodResearchPayload,
    FloodResearchToolResponse,
    ListingFieldProvenancePayload,
    ListingFieldProvenanceToolResponse,
    ListingHistoryPayload,
    ListingHistoryToolResponse,
    ListingSnapshotPayload,
    ListingSnapshotToolResponse,
    NeighborhoodSummaryPayload,
    NeighborhoodSummaryToolResponse,
    PermitHistoryPayload,
    PermitHistoryToolResponse,
    PublicRecordsSummaryPayload,
    PublicRecordsSummaryToolResponse,
    RentalCompsPayload,
    RentalCompsToolResponse,
    SalesCompsPayload,
    SalesCompsToolResponse,
    SchoolResearchPayload,
    SchoolResearchToolResponse,
    TaxHistoryPayload,
    TaxHistoryToolResponse,
    ToolErrorDetail,
    TransactionHistoryPayload,
    TransactionHistoryToolResponse,
    UnderwritingSummaryPayload,
    UnderwritingSummaryToolResponse,
)
from app.agent_research.versioning import AgentName
from app.exceptions import AppError
from app.models.comparables import (
    RentalCompsResearchRequest,
    RentalCompsResearchResponse,
    SalesCompsResearchRequest,
    SalesCompsResearchResponse,
)
from app.models.neighborhood import NeighborhoodResearchRequest, NeighborhoodResearchResponse
from app.models.public_records import (
    PublicRecordsResearchRequest,
    PublicRecordsResearchResponse,
)
from app.models.research import ResearchResult


def _translate_tool_error(error: Exception) -> ToolErrorDetail:
    if isinstance(error, AppError):
        return ToolErrorDetail(
            code=error.code,
            message=error.message,
            retryable=error.retryable,
        )
    return ToolErrorDetail(
        code="unexpected_tool_error",
        message="An unexpected tool error occurred.",
        retryable=False,
    )


def _success[T, R: BaseModel](
    response_type: type[R],
    data: T,
    warnings: list[str] | None = None,
) -> R:
    return response_type(success=True, data=data, warnings=warnings or [])


def _failure[R: BaseModel](
    response_type: type[R],
    error: Exception,
    warnings: list[str] | None = None,
) -> R:
    return response_type(
        success=False,
        error=_translate_tool_error(error),
        warnings=warnings or [],
    )


async def _load_public_records_result(
    context: AgentRunContext,
) -> ResearchResult[Any]:
    if context.research_package.public_records is not None:
        return context.research_package.public_records
    service = context.research_services.public_records_service
    if service is None:
        raise MissingAgentInputError(message="Public-records service is not configured.")
    response: PublicRecordsResearchResponse = await service.research(
        PublicRecordsResearchRequest(property=context.verified_property)
    )
    if response.result is None:
        raise MissingAgentInputError(message="Public-records data is not available.")
    return response.result


async def _load_sales_comps_result(
    context: AgentRunContext,
) -> ResearchResult[Any]:
    if context.research_package.sales_comps is not None:
        return context.research_package.sales_comps
    service = context.research_services.sales_comps_service
    if service is None:
        raise MissingAgentInputError(message="Sales comparable service is not configured.")
    response: SalesCompsResearchResponse = await service.research(
        SalesCompsResearchRequest(property=context.verified_property)
    )
    if response.result is None:
        raise MissingAgentInputError(message="Sales comparable data is not available.")
    return response.result


async def _load_rental_comps_result(
    context: AgentRunContext,
) -> ResearchResult[Any]:
    if context.research_package.rental_comps is not None:
        return context.research_package.rental_comps
    service = context.research_services.rental_comps_service
    if service is None:
        raise MissingAgentInputError(message="Rental comparable service is not configured.")
    response: RentalCompsResearchResponse = await service.research(
        RentalCompsResearchRequest(property=context.verified_property)
    )
    if response.result is None:
        raise MissingAgentInputError(message="Rental comparable data is not available.")
    return response.result


async def _load_neighborhood_result(
    context: AgentRunContext,
) -> ResearchResult[Any]:
    if context.research_package.neighborhood is not None:
        return context.research_package.neighborhood
    service = context.research_services.neighborhood_service
    if service is None:
        raise MissingAgentInputError(message="Neighborhood service is not configured.")
    response: NeighborhoodResearchResponse = await service.research(
        NeighborhoodResearchRequest(property=context.verified_property)
    )
    if response.result is None:
        raise MissingAgentInputError(message="Neighborhood data is not available.")
    return response.result


async def get_listing_snapshot_impl(
    context: AgentRunContext,
) -> ListingSnapshotToolResponse:
    try:
        if context.listing_extraction is None:
            raise MissingAgentInputError(message="Listing extraction data is not available.")
        property_key = build_property_key(context.verified_property)
        sanitized_property, property_warnings = sanitize_for_agent(
            context.listing_extraction.property
        )
        payload = ListingSnapshotPayload(
            provider=context.listing_extraction.provider,
            source_url=context.listing_extraction.source_url,
            metadata=context.listing_extraction.metadata,
            property=sanitized_property,
            field_provenance=[
                ListingFieldProvenancePayload(
                    field_name=field_name,
                    value=field.value,
                    raw_value=field.raw_value,
                    source=field.source,
                    confidence=field.confidence,
                )
                for field_name, field in context.listing_extraction.field_provenance.items()
            ],
            source_ids=[f"{property_key}:listing_extraction"],
            citation_ids=[],
        )
        sanitized_payload, payload_warnings = sanitize_for_agent(payload)
        return _success(
            ListingSnapshotToolResponse,
            sanitized_payload,
            warnings=[*property_warnings, *payload_warnings],
        )
    except Exception as exc:
        return _failure(ListingSnapshotToolResponse, exc)


async def get_listing_price_history_impl(
    context: AgentRunContext,
) -> ListingHistoryToolResponse:
    try:
        if context.listing_extraction is None:
            raise MissingAgentInputError(message="Listing extraction data is not available.")
        property_key = build_property_key(context.verified_property)
        payload = ListingHistoryPayload(
            price_history=context.listing_extraction.property.price_history,
            sale_history=context.listing_extraction.property.sale_history,
            source_ids=[f"{property_key}:listing_extraction"],
        )
        sanitized_payload, warnings = sanitize_for_agent(payload)
        return _success(ListingHistoryToolResponse, sanitized_payload, warnings=warnings)
    except Exception as exc:
        return _failure(ListingHistoryToolResponse, exc)


async def get_listing_field_provenance_impl(
    context: AgentRunContext,
    *,
    field_name: str,
) -> ListingFieldProvenanceToolResponse:
    try:
        if context.listing_extraction is None:
            raise MissingAgentInputError(message="Listing extraction data is not available.")
        field = context.listing_extraction.field_provenance.get(field_name)
        if field is None:
            raise MissingAgentInputError(message=f"Listing field '{field_name}' is not available.")
        payload = ListingFieldProvenancePayload(
            field_name=field_name,
            value=field.value,
            raw_value=field.raw_value,
            source=field.source,
            confidence=field.confidence,
        )
        sanitized_payload, warnings = sanitize_for_agent(payload)
        return _success(ListingFieldProvenanceToolResponse, sanitized_payload, warnings=warnings)
    except Exception as exc:
        return _failure(ListingFieldProvenanceToolResponse, exc)


async def get_public_record_facts_impl(
    context: AgentRunContext,
) -> PublicRecordsSummaryToolResponse:
    try:
        result = await _load_public_records_result(context)
        evidence_index = build_evidence_index(context)
        source_ids = source_ids_for_label(evidence_index, "research:public_records:source:")
        payload = PublicRecordsSummaryPayload(
            provider=result.provider,
            retrieved_at=result.retrieved_at,
            cache_status=result.metadata.cache_status,
            source_ids=source_ids,
            citation_ids=citation_ids_for_source_ids(evidence_index, source_ids),
            assessed_value=result.data.assessed_value.value,
            ownership=result.data.ownership.value or [],
            parcel=result.data.parcel.value,
            flood_zone=result.data.flood_zone.value,
            building_characteristics=result.data.building_characteristics.value,
            validations=result.data.validations.value,
            warnings=result.metadata.warnings,
        )
        sanitized_payload, warnings = sanitize_for_agent(payload)
        return _success(PublicRecordsSummaryToolResponse, sanitized_payload, warnings=warnings)
    except Exception as exc:
        return _failure(PublicRecordsSummaryToolResponse, exc)


async def get_property_tax_history_impl(
    context: AgentRunContext,
) -> TaxHistoryToolResponse:
    try:
        result = await _load_public_records_result(context)
        evidence_index = build_evidence_index(context)
        source_ids = source_ids_for_label(evidence_index, "research:public_records:source:")
        payload = TaxHistoryPayload(
            provider=result.provider,
            retrieved_at=result.retrieved_at,
            source_ids=source_ids,
            citation_ids=citation_ids_for_source_ids(evidence_index, source_ids),
            tax_history=result.data.tax_history.value or [],
            assessed_value=result.data.assessed_value.value,
        )
        sanitized_payload, warnings = sanitize_for_agent(payload)
        return _success(TaxHistoryToolResponse, sanitized_payload, warnings=warnings)
    except Exception as exc:
        return _failure(TaxHistoryToolResponse, exc)


async def get_permit_history_impl(
    context: AgentRunContext,
    *,
    limit: int,
) -> PermitHistoryToolResponse:
    try:
        result = await _load_public_records_result(context)
        evidence_index = build_evidence_index(context)
        source_ids = source_ids_for_label(evidence_index, "research:public_records:source:")
        payload = PermitHistoryPayload(
            provider=result.provider,
            retrieved_at=result.retrieved_at,
            source_ids=source_ids,
            citation_ids=citation_ids_for_source_ids(evidence_index, source_ids),
            permits=(result.data.permits.value or [])[:limit],
        )
        sanitized_payload, warnings = sanitize_for_agent(payload)
        return _success(PermitHistoryToolResponse, sanitized_payload, warnings=warnings)
    except Exception as exc:
        return _failure(PermitHistoryToolResponse, exc)


async def get_transaction_history_impl(
    context: AgentRunContext,
    *,
    limit: int,
) -> TransactionHistoryToolResponse:
    try:
        result = await _load_public_records_result(context)
        evidence_index = build_evidence_index(context)
        source_ids = source_ids_for_label(evidence_index, "research:public_records:source:")
        payload = TransactionHistoryPayload(
            provider=result.provider,
            retrieved_at=result.retrieved_at,
            source_ids=source_ids,
            citation_ids=citation_ids_for_source_ids(evidence_index, source_ids),
            deeds=(result.data.deeds.value or [])[:limit],
            sale_history=(result.data.sale_history.value or [])[:limit],
        )
        sanitized_payload, warnings = sanitize_for_agent(payload)
        return _success(TransactionHistoryToolResponse, sanitized_payload, warnings=warnings)
    except Exception as exc:
        return _failure(TransactionHistoryToolResponse, exc)


async def get_sales_comparables_impl(
    context: AgentRunContext,
    *,
    limit: int,
) -> SalesCompsToolResponse:
    try:
        result = await _load_sales_comps_result(context)
        evidence_index = build_evidence_index(context)
        source_ids = source_ids_for_label(evidence_index, "research:sales_comps:source:")
        payload = SalesCompsPayload(
            provider=result.provider,
            retrieved_at=result.retrieved_at,
            cache_status=result.metadata.cache_status,
            source_ids=source_ids,
            citation_ids=citation_ids_for_source_ids(evidence_index, source_ids),
            top_comparables=result.data.top_comparables[:limit],
            summary=result.data.summary,
            warnings=result.metadata.warnings,
        )
        sanitized_payload, warnings = sanitize_for_agent(payload)
        return _success(SalesCompsToolResponse, sanitized_payload, warnings=warnings)
    except Exception as exc:
        return _failure(SalesCompsToolResponse, exc)


async def get_rental_comparables_impl(
    context: AgentRunContext,
    *,
    limit: int,
) -> RentalCompsToolResponse:
    try:
        result = await _load_rental_comps_result(context)
        evidence_index = build_evidence_index(context)
        source_ids = source_ids_for_label(evidence_index, "research:rental_comps:source:")
        payload = RentalCompsPayload(
            provider=result.provider,
            retrieved_at=result.retrieved_at,
            cache_status=result.metadata.cache_status,
            source_ids=source_ids,
            citation_ids=citation_ids_for_source_ids(evidence_index, source_ids),
            best_comparables=result.data.best_comparables[:limit],
            summary=result.data.summary,
            warnings=result.metadata.warnings,
        )
        sanitized_payload, warnings = sanitize_for_agent(payload)
        return _success(RentalCompsToolResponse, sanitized_payload, warnings=warnings)
    except Exception as exc:
        return _failure(RentalCompsToolResponse, exc)


async def get_neighborhood_research_impl(
    context: AgentRunContext,
) -> NeighborhoodSummaryToolResponse:
    try:
        result = await _load_neighborhood_result(context)
        evidence_index = build_evidence_index(context)
        source_ids = source_ids_for_label(evidence_index, "research:neighborhood:source:")
        payload = NeighborhoodSummaryPayload(
            provider=result.provider,
            retrieved_at=result.retrieved_at,
            cache_status=result.metadata.cache_status,
            source_ids=source_ids,
            citation_ids=citation_ids_for_source_ids(evidence_index, source_ids),
            neighborhood=result.data,
            warnings=result.metadata.warnings,
        )
        sanitized_payload, warnings = sanitize_for_agent(payload)
        return _success(NeighborhoodSummaryToolResponse, sanitized_payload, warnings=warnings)
    except Exception as exc:
        return _failure(NeighborhoodSummaryToolResponse, exc)


async def get_school_research_impl(
    context: AgentRunContext,
    *,
    limit: int,
) -> SchoolResearchToolResponse:
    try:
        result = await _load_neighborhood_result(context)
        evidence_index = build_evidence_index(context)
        source_ids = source_ids_for_label(evidence_index, "research:neighborhood:source:")
        payload = SchoolResearchPayload(
            provider=result.provider,
            retrieved_at=result.retrieved_at,
            cache_status=result.metadata.cache_status,
            source_ids=source_ids,
            citation_ids=citation_ids_for_source_ids(evidence_index, source_ids),
            nearby_schools=(result.data.nearby_schools.value or [])[:limit],
            school_rating_average=result.data.school_rating_average.value,
            warnings=result.metadata.warnings,
        )
        sanitized_payload, warnings = sanitize_for_agent(payload)
        return _success(SchoolResearchToolResponse, sanitized_payload, warnings=warnings)
    except Exception as exc:
        return _failure(SchoolResearchToolResponse, exc)


async def get_flood_research_impl(
    context: AgentRunContext,
) -> FloodResearchToolResponse:
    try:
        result = await _load_neighborhood_result(context)
        evidence_index = build_evidence_index(context)
        source_ids = source_ids_for_label(evidence_index, "research:neighborhood:source:")
        payload = FloodResearchPayload(
            provider=result.provider,
            retrieved_at=result.retrieved_at,
            cache_status=result.metadata.cache_status,
            source_ids=source_ids,
            citation_ids=citation_ids_for_source_ids(evidence_index, source_ids),
            flood_risk=result.data.flood_risk.value,
            warnings=result.metadata.warnings,
        )
        sanitized_payload, warnings = sanitize_for_agent(payload)
        return _success(FloodResearchToolResponse, sanitized_payload, warnings=warnings)
    except Exception as exc:
        return _failure(FloodResearchToolResponse, exc)


async def get_underwriting_summary_impl(
    context: AgentRunContext,
) -> UnderwritingSummaryToolResponse:
    try:
        if context.underwriting_result is None:
            raise MissingAgentInputError(message="Underwriting analysis is not available.")
        property_key = build_property_key(context.verified_property)
        analysis = context.underwriting_result
        payload = UnderwritingSummaryPayload(
            property=context.verified_property,
            purchase_price=analysis.acquisition.purchase_price,
            monthly_scheduled_rent=analysis.income.monthly_scheduled_rent,
            noi=analysis.metrics.noi,
            monthly_pre_tax_cash_flow=analysis.metrics.monthly_pre_tax_cash_flow,
            cap_rate=analysis.metrics.cap_rate,
            cash_on_cash_return=analysis.metrics.cash_on_cash_return,
            dscr=analysis.metrics.dscr,
            binding_maximum_price=analysis.maximum_offer.binding_maximum_price,
            scenario_names=[scenario.name for scenario in analysis.scenarios],
            stress_test_ids=[stress_test.identifier for stress_test in analysis.stress_tests],
            warnings=analysis.warnings,
            source_ids=[f"{property_key}:underwriting"],
        )
        sanitized_payload, warnings = sanitize_for_agent(payload)
        return _success(UnderwritingSummaryToolResponse, sanitized_payload, warnings=warnings)
    except Exception as exc:
        return _failure(UnderwritingSummaryToolResponse, exc)


@function_tool(output_type=ListingSnapshotToolResponse, failure_error_function=None)
async def get_listing_snapshot(
    run_context: RunContextWrapper[AgentRunContext],
) -> ListingSnapshotToolResponse:
    """Return the sanitized listing snapshot and field provenance for the current property."""

    return await get_listing_snapshot_impl(run_context.context)


@function_tool(output_type=ListingHistoryToolResponse, failure_error_function=None)
async def get_listing_price_history(
    run_context: RunContextWrapper[AgentRunContext],
) -> ListingHistoryToolResponse:
    """Return listing price history and sale history for the current property."""

    return await get_listing_price_history_impl(run_context.context)


@function_tool(
    output_type=ListingFieldProvenanceToolResponse,
    failure_error_function=None,
)
async def get_listing_field_provenance(
    run_context: RunContextWrapper[AgentRunContext],
    field_name: Annotated[str, Field(min_length=1)],
) -> ListingFieldProvenanceToolResponse:
    """Return sanitized provenance for one extracted listing field."""

    return await get_listing_field_provenance_impl(
        run_context.context,
        field_name=field_name,
    )


@function_tool(output_type=PublicRecordsSummaryToolResponse, failure_error_function=None)
async def get_public_record_facts(
    run_context: RunContextWrapper[AgentRunContext],
) -> PublicRecordsSummaryToolResponse:
    """Return the key public-record facts already loaded for the current property."""

    return await get_public_record_facts_impl(run_context.context)


@function_tool(output_type=TaxHistoryToolResponse, failure_error_function=None)
async def get_property_tax_history(
    run_context: RunContextWrapper[AgentRunContext],
) -> TaxHistoryToolResponse:
    """Return tax-history and assessed-value records for the current property."""

    return await get_property_tax_history_impl(run_context.context)


@function_tool(output_type=PermitHistoryToolResponse, failure_error_function=None)
async def get_permit_history(
    run_context: RunContextWrapper[AgentRunContext],
    limit: Annotated[int, Field(ge=1, le=25)] = 10,
) -> PermitHistoryToolResponse:
    """Return permit-history records for the current property."""

    return await get_permit_history_impl(run_context.context, limit=limit)


@function_tool(output_type=TransactionHistoryToolResponse, failure_error_function=None)
async def get_transaction_history(
    run_context: RunContextWrapper[AgentRunContext],
    limit: Annotated[int, Field(ge=1, le=25)] = 10,
) -> TransactionHistoryToolResponse:
    """Return deed and sale-history records for the current property."""

    return await get_transaction_history_impl(run_context.context, limit=limit)


@function_tool(output_type=SalesCompsToolResponse, failure_error_function=None)
async def get_sales_comparables(
    run_context: RunContextWrapper[AgentRunContext],
    limit: Annotated[int, Field(ge=1, le=10)] = 5,
) -> SalesCompsToolResponse:
    """Return the ranked sales comparables already computed for the current property."""

    return await get_sales_comparables_impl(run_context.context, limit=limit)


@function_tool(output_type=RentalCompsToolResponse, failure_error_function=None)
async def get_rental_comparables(
    run_context: RunContextWrapper[AgentRunContext],
    limit: Annotated[int, Field(ge=1, le=10)] = 5,
) -> RentalCompsToolResponse:
    """Return the ranked rental comparables already computed for the current property."""

    return await get_rental_comparables_impl(run_context.context, limit=limit)


@function_tool(output_type=NeighborhoodSummaryToolResponse, failure_error_function=None)
async def get_neighborhood_research(
    run_context: RunContextWrapper[AgentRunContext],
) -> NeighborhoodSummaryToolResponse:
    """Return the sanitized neighborhood research package for the current property."""

    return await get_neighborhood_research_impl(run_context.context)


@function_tool(output_type=SchoolResearchToolResponse, failure_error_function=None)
async def get_school_research(
    run_context: RunContextWrapper[AgentRunContext],
    limit: Annotated[int, Field(ge=1, le=20)] = 10,
) -> SchoolResearchToolResponse:
    """Return the school subset of neighborhood research for the current property."""

    return await get_school_research_impl(run_context.context, limit=limit)


@function_tool(output_type=FloodResearchToolResponse, failure_error_function=None)
async def get_flood_research(
    run_context: RunContextWrapper[AgentRunContext],
) -> FloodResearchToolResponse:
    """Return the flood-risk subset of neighborhood research for the current property."""

    return await get_flood_research_impl(run_context.context)


@function_tool(output_type=UnderwritingSummaryToolResponse, failure_error_function=None)
async def get_underwriting_summary(
    run_context: RunContextWrapper[AgentRunContext],
) -> UnderwritingSummaryToolResponse:
    """Return the read-only deterministic underwriting summary for the current property."""

    return await get_underwriting_summary_impl(run_context.context)


LISTING_TOOLS = (
    get_listing_snapshot,
    get_listing_price_history,
    get_listing_field_provenance,
)
PUBLIC_RECORDS_TOOLS = (
    get_public_record_facts,
    get_property_tax_history,
    get_permit_history,
    get_transaction_history,
)
COMPARABLE_TOOLS = (
    get_sales_comparables,
    get_rental_comparables,
    get_underwriting_summary,
)
NEIGHBORHOOD_TOOLS = (
    get_neighborhood_research,
    get_school_research,
    get_flood_research,
)
RISK_TOOLS = (
    get_listing_snapshot,
    get_public_record_facts,
    get_neighborhood_research,
    get_underwriting_summary,
)

AGENT_TOOLSETS: dict[AgentName, tuple[Any, ...]] = {
    AgentName.LISTING: LISTING_TOOLS,
    AgentName.PUBLIC_RECORDS: PUBLIC_RECORDS_TOOLS,
    AgentName.COMPARABLE: COMPARABLE_TOOLS,
    AgentName.NEIGHBORHOOD: NEIGHBORHOOD_TOOLS,
    AgentName.PROPERTY_RISK: RISK_TOOLS,
}


def tools_for_agent(agent_name: AgentName) -> tuple[Any, ...]:
    """Return the approved tool subset for a specialist agent."""

    return AGENT_TOOLSETS.get(agent_name, ())
