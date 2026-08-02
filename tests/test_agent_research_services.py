"""Tests for independent specialist-agent service wrappers."""

from __future__ import annotations

import json

import pytest

from app.agent_research.exceptions import AgentGuardrailFailureError
from app.agent_research.services import (
    ComparableAgentService,
    ListingAgentService,
    NeighborhoodAgentService,
    PublicRecordsAgentService,
)
from app.agent_research.specialist_models import (
    ComparableAgentInput,
    ListingAgentInput,
    NeighborhoodAgentInput,
    PublicRecordsAgentInput,
)
from tests.agent_sdk_utils import (
    StubAgentRunner,
    make_agent_context,
    make_comparable_agent_output,
    make_listing_agent_output,
    make_neighborhood_agent_output,
    make_public_records_agent_output,
)


@pytest.mark.asyncio
async def test_listing_agent_service_runs_with_narrow_input() -> None:
    runner = StubAgentRunner(make_listing_agent_output())
    service = ListingAgentService(runner=runner)

    output = await service.run(make_agent_context())

    assert output.agent_name == "listing_agent"
    payload = json.loads(runner.calls[0]["agent_input"])
    validated = ListingAgentInput.model_validate(payload)
    assert validated.listing_snapshot.provider == "zillow"
    assert "public_records_summary" not in payload


@pytest.mark.asyncio
async def test_public_records_agent_service_runs_independently() -> None:
    runner = StubAgentRunner(make_public_records_agent_output())
    service = PublicRecordsAgentService(runner=runner)

    output = await service.run(make_agent_context())

    assert output.agent_name == "public_records_agent"
    payload = json.loads(runner.calls[0]["agent_input"])
    validated = PublicRecordsAgentInput.model_validate(payload)
    assert validated.public_records_summary.assessed_value == 285000


@pytest.mark.asyncio
async def test_comparable_agent_service_runs_independently() -> None:
    runner = StubAgentRunner(make_comparable_agent_output())
    service = ComparableAgentService(runner=runner)

    output = await service.run(make_agent_context())

    assert output.agent_name == "comparable_agent"
    payload = json.loads(runner.calls[0]["agent_input"])
    validated = ComparableAgentInput.model_validate(payload)
    assert validated.sales_comparables.top_comparables


@pytest.mark.asyncio
async def test_neighborhood_agent_service_blocks_fair_housing_output() -> None:
    output = make_neighborhood_agent_output()
    output.summary = "This area is ideal for young professionals."
    runner = StubAgentRunner(output)
    service = NeighborhoodAgentService(runner=runner)

    with pytest.raises(AgentGuardrailFailureError):
        await service.run(make_agent_context())


@pytest.mark.asyncio
async def test_neighborhood_agent_service_runs_with_narrow_input() -> None:
    runner = StubAgentRunner(make_neighborhood_agent_output())
    service = NeighborhoodAgentService(runner=runner)

    output = await service.run(make_agent_context())

    assert output.agent_name == "neighborhood_agent"
    payload = json.loads(runner.calls[0]["agent_input"])
    validated = NeighborhoodAgentInput.model_validate(payload)
    assert validated.school_research.nearby_schools
