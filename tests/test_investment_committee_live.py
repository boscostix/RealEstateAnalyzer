"""Optional live integration test for the OpenAI-backed investment-committee workflow."""

from __future__ import annotations

import os

import pytest

from app.investment_committee.services import InvestmentCommitteeService
from tests.test_investment_committee_policies import make_committee_input


def _live_tests_enabled() -> bool:
    return os.getenv("ENABLE_LIVE_INVESTMENT_COMMITTEE_TESTS", "false").lower() == "true"


pytestmark = pytest.mark.skipif(
    not _live_tests_enabled() or not os.getenv("OPENAI_API_KEY"),
    reason=(
        "Set ENABLE_LIVE_INVESTMENT_COMMITTEE_TESTS=true and OPENAI_API_KEY "
        "to run live committee tests."
    ),
)


@pytest.mark.asyncio
async def test_live_investment_committee_returns_structured_output() -> None:
    service = InvestmentCommitteeService()
    output = await service.analyze(
        request_id="req-live-committee",
        analysis_id="analysis-live-committee",
        committee_input=make_committee_input(),
    )

    assert output.recommendation
    assert output.recommendation_summary
    assert output.evidence_references
