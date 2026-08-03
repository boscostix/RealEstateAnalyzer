"""Optional live integration test for the OpenAI-backed agent workflow."""

from __future__ import annotations

import os

import pytest

from app.agent_research.services import ListingAgentService
from tests.agent_sdk_utils import make_agent_context


def _live_tests_enabled() -> bool:
    return os.getenv("ENABLE_LIVE_AGENT_RESEARCH_TESTS", "false").lower() == "true"


pytestmark = pytest.mark.skipif(
    not _live_tests_enabled() or not os.getenv("OPENAI_API_KEY"),
    reason=(
        "Set ENABLE_LIVE_AGENT_RESEARCH_TESTS=true and OPENAI_API_KEY to run live agent tests."
    ),
)


@pytest.mark.asyncio
async def test_live_listing_agent_returns_structured_output() -> None:
    service = ListingAgentService()
    output = await service.run(make_agent_context())

    assert output.agent_name == "listing_agent"
    assert output.agent_version
    assert output.prompt_version
    assert isinstance(output.summary, str)
