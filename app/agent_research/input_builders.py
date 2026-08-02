"""Agent-specific input builders that pass only relevant deterministic data."""

from __future__ import annotations

from decimal import Decimal

from app.agent_research.context import AgentRunContext
from app.agent_research.evidence import build_property_key
from app.agent_research.exceptions import MissingAgentInputError
from app.agent_research.models import DuplicateFindingGroup, ResearchConflict
from app.agent_research.risk_models import PropertyRiskAgentInput, RiskStressTestSummary
from app.agent_research.specialist_models import (
    ComparableAgentInput,
    ComparableAgentOutput,
    ListingAgentInput,
    ListingAgentOutput,
    NeighborhoodAgentInput,
    NeighborhoodAgentOutput,
    PublicRecordsAgentInput,
    PublicRecordsAgentOutput,
)
from app.agent_research.tools import (
    get_flood_research_impl,
    get_listing_price_history_impl,
    get_listing_snapshot_impl,
    get_neighborhood_research_impl,
    get_property_tax_history_impl,
    get_public_record_facts_impl,
    get_rental_comparables_impl,
    get_sales_comparables_impl,
    get_school_research_impl,
    get_transaction_history_impl,
    get_underwriting_summary_impl,
)


def _unresolved_verified_fields(context: AgentRunContext) -> list[str]:
    unresolved: list[str] = []
    for field_name, field_value in context.verified_property.model_dump(mode="python").items():
        if field_name in {"source_url", "provider"}:
            continue
        if isinstance(field_value, dict) and field_value.get("status") != "verified":
            unresolved.append(field_name)
    return unresolved


async def build_listing_agent_input(context: AgentRunContext) -> ListingAgentInput:
    listing_snapshot = await get_listing_snapshot_impl(context)
    listing_history = await get_listing_price_history_impl(context)
    if listing_snapshot.data is None or listing_history.data is None:
        raise MissingAgentInputError(message="Listing-agent input could not be prepared.")
    return ListingAgentInput(
        property_key=build_property_key(context.verified_property),
        request_id=context.request_id,
        analysis_id=context.analysis_id,
        verified_property=context.verified_property,
        listing_snapshot=listing_snapshot.data,
        listing_history=listing_history.data,
        unresolved_verified_fields=_unresolved_verified_fields(context),
    )


async def build_public_records_agent_input(context: AgentRunContext) -> PublicRecordsAgentInput:
    public_records = await get_public_record_facts_impl(context)
    tax_history = await get_property_tax_history_impl(context)
    transaction_history = await get_transaction_history_impl(context, limit=10)
    if public_records.data is None or tax_history.data is None or transaction_history.data is None:
        raise MissingAgentInputError(message="Public-records agent input could not be prepared.")
    return PublicRecordsAgentInput(
        property_key=build_property_key(context.verified_property),
        request_id=context.request_id,
        analysis_id=context.analysis_id,
        verified_property=context.verified_property,
        public_records_summary=public_records.data,
        tax_history=tax_history.data,
        transaction_history=transaction_history.data,
    )


async def build_comparable_agent_input(context: AgentRunContext) -> ComparableAgentInput:
    sales = await get_sales_comparables_impl(context, limit=5)
    rentals = await get_rental_comparables_impl(context, limit=5)
    underwriting = await get_underwriting_summary_impl(context)
    if sales.data is None or rentals.data is None:
        raise MissingAgentInputError(message="Comparable-agent input could not be prepared.")
    return ComparableAgentInput(
        property_key=build_property_key(context.verified_property),
        request_id=context.request_id,
        analysis_id=context.analysis_id,
        verified_property=context.verified_property,
        sales_comparables=sales.data,
        rental_comparables=rentals.data,
        underwriting_summary=underwriting.data,
    )


async def build_neighborhood_agent_input(context: AgentRunContext) -> NeighborhoodAgentInput:
    neighborhood = await get_neighborhood_research_impl(context)
    schools = await get_school_research_impl(context, limit=10)
    flood = await get_flood_research_impl(context)
    if neighborhood.data is None or schools.data is None or flood.data is None:
        raise MissingAgentInputError(message="Neighborhood-agent input could not be prepared.")
    return NeighborhoodAgentInput(
        property_key=build_property_key(context.verified_property),
        request_id=context.request_id,
        analysis_id=context.analysis_id,
        verified_property=context.verified_property,
        neighborhood_summary=neighborhood.data,
        school_research=schools.data,
        flood_research=flood.data,
    )


def _risk_stress_tests(context: AgentRunContext) -> list[RiskStressTestSummary]:
    if context.underwriting_result is None:
        return []
    return [
        RiskStressTestSummary(
            identifier=stress_test.identifier,
            description=stress_test.description,
            change_in_monthly_cash_flow=stress_test.change_in_monthly_cash_flow,
            additional_cash_required=stress_test.additional_cash_required,
            cash_flow_remains_positive=stress_test.cash_flow_remains_positive,
            stressed_dscr=stress_test.stressed_metrics.dscr,
            warnings=stress_test.warnings,
        )
        for stress_test in context.underwriting_result.stress_tests
    ]


async def build_property_risk_agent_input(
    context: AgentRunContext,
    *,
    listing_analysis: ListingAgentOutput,
    public_records_analysis: PublicRecordsAgentOutput,
    comparable_analysis: ComparableAgentOutput,
    neighborhood_analysis: NeighborhoodAgentOutput,
    conflicts: list[ResearchConflict],
    duplicate_findings: list[DuplicateFindingGroup],
    upstream_data_confidence: Decimal,
    upstream_warnings: list[str] | None = None,
) -> PropertyRiskAgentInput:
    underwriting = await get_underwriting_summary_impl(context)
    return PropertyRiskAgentInput(
        property_key=build_property_key(context.verified_property),
        request_id=context.request_id,
        analysis_id=context.analysis_id,
        verified_property=context.verified_property,
        listing_analysis=listing_analysis,
        public_records_analysis=public_records_analysis,
        comparable_analysis=comparable_analysis,
        neighborhood_analysis=neighborhood_analysis,
        conflicts=conflicts,
        duplicate_findings=duplicate_findings,
        upstream_data_confidence=upstream_data_confidence,
        underwriting_summary=underwriting.data,
        stress_tests=_risk_stress_tests(context),
        upstream_warnings=upstream_warnings or [],
    )
