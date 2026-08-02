"""Tests for specialist-agent input builders."""

from __future__ import annotations

from app.agent_research.input_builders import (
    build_comparable_agent_input,
    build_listing_agent_input,
    build_neighborhood_agent_input,
    build_public_records_agent_input,
)
from tests.agent_sdk_utils import make_agent_context, make_underwriting_analysis


async def test_listing_input_builder_only_includes_listing_specific_payloads() -> None:
    built = await build_listing_agent_input(make_agent_context())

    assert built.listing_snapshot.provider == "zillow"
    assert built.listing_history.source_ids
    assert "asking_price" in built.verified_property.model_dump(mode="python")
    assert not hasattr(built, "public_records_summary")


async def test_public_records_input_builder_includes_public_records_only() -> None:
    built = await build_public_records_agent_input(make_agent_context())

    assert built.public_records_summary.assessed_value == 285000
    assert built.tax_history.tax_history
    assert built.transaction_history.deeds == []


async def test_comparable_input_builder_includes_underwriting_when_available() -> None:
    built = await build_comparable_agent_input(
        make_agent_context(underwriting_result=make_underwriting_analysis())
    )

    assert built.sales_comparables.top_comparables
    assert built.rental_comparables.best_comparables
    assert built.underwriting_summary is not None
    assert built.underwriting_summary.purchase_price == 300000


async def test_neighborhood_input_builder_is_narrow_and_sanitized() -> None:
    built = await build_neighborhood_agent_input(make_agent_context())

    assert built.neighborhood_summary.neighborhood.flood_risk.value is not None
    assert built.school_research.nearby_schools
    assert built.flood_research.flood_risk is not None
