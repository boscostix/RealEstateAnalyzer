"""Tests for agent tool wrappers and sanitization."""

from __future__ import annotations

from app.agent_research.tools import (
    get_listing_field_provenance_impl,
    get_listing_snapshot_impl,
    get_property_tax_history_impl,
    get_public_record_facts_impl,
    get_sales_comparables_impl,
    get_underwriting_summary_impl,
)
from tests.agent_sdk_utils import make_agent_context, make_underwriting_analysis


async def test_listing_snapshot_sanitizes_prompt_injection_text() -> None:
    context = make_agent_context()

    response = await get_listing_snapshot_impl(context)

    assert response.success is True
    assert response.data is not None
    assert "prompt_injection_filtered" in response.warnings
    assert response.data.property.description == "[filtered untrusted text removed]"
    assert response.data.source_ids[0].startswith("property:")


async def test_listing_field_provenance_sanitizes_raw_value() -> None:
    context = make_agent_context()

    response = await get_listing_field_provenance_impl(context, field_name="description")

    assert response.success is True
    assert response.data is not None
    assert response.data.raw_value == "[filtered untrusted text removed]"


async def test_public_record_tool_preserves_provenance_ids() -> None:
    context = make_agent_context()

    response = await get_public_record_facts_impl(context)

    assert response.success is True
    assert response.data is not None
    assert response.data.source_ids
    assert response.data.citation_ids
    assert response.data.source_ids[0].startswith("property:")
    assert response.data.citation_ids[0].startswith(response.data.source_ids[0])


async def test_public_record_tool_falls_back_to_service_when_package_missing() -> None:
    context = make_agent_context()
    expected_result = context.research_package.public_records
    assert expected_result is not None
    context.research_package = context.research_package.model_copy(update={"public_records": None})

    class StubPublicRecordsService:
        async def research(self, request: object) -> object:
            from app.models.public_records import PublicRecordsResearchResponse

            return PublicRecordsResearchResponse(success=True, result=expected_result)

    context.research_services.public_records_service = StubPublicRecordsService()

    response = await get_property_tax_history_impl(context)

    assert response.success is True
    assert response.data is not None
    assert response.data.tax_history[0].tax_year == 2025


async def test_underwriting_summary_returns_structured_error_when_missing() -> None:
    context = make_agent_context()

    response = await get_underwriting_summary_impl(context)

    assert response.success is False
    assert response.error is not None
    assert response.error.code == "missing_agent_input"


async def test_underwriting_summary_returns_read_only_payload() -> None:
    context = make_agent_context(underwriting_result=make_underwriting_analysis())

    response = await get_underwriting_summary_impl(context)

    assert response.success is True
    assert response.data is not None
    assert response.data.source_ids[0].endswith(":underwriting")


async def test_sales_comps_tool_returns_ranked_results() -> None:
    context = make_agent_context()

    response = await get_sales_comparables_impl(context, limit=1)

    assert response.success is True
    assert response.data is not None
    assert len(response.data.top_comparables) == 1
    assert response.data.summary.comparable_count == 1
