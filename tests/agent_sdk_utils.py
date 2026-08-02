"""Mock utilities for OpenAI Agents SDK tests."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from app.agent_research.models import AgentExecutionMetadata, AgentResearchOutput
from app.agent_research.versioning import WORKFLOW_NAME, WORKFLOW_VERSION


class MockRunResult:
    """Tiny stand-in for `agents.result.RunResult`."""

    def __init__(self, output: object) -> None:
        self._output = output

    def final_output_as(self, output_type: type[object]) -> object:
        if not isinstance(self._output, output_type):
            raise TypeError("Unexpected output type.")
        return self._output


def make_agent_output(agent_name: str = "listing_agent") -> AgentResearchOutput:
    """Create a valid specialist-agent output for tests."""

    return AgentResearchOutput(
        agent_name=agent_name,
        agent_version=f"{agent_name}:v1",
        prompt_version="v1",
        summary="Structured summary.",
        overall_confidence=Decimal("0.80"),
        findings=[],
        conflicts=[],
        missing_information=["roof age"],
        due_diligence_questions=["When was the roof last replaced?"],
        sources_used=["listing_source_1"],
        warnings=[],
    )


def make_execution_metadata() -> AgentExecutionMetadata:
    """Create a valid execution-metadata object for synthesized outputs."""

    started_at = datetime.now(UTC)
    return AgentExecutionMetadata(
        request_id="req-123",
        workflow_name=WORKFLOW_NAME,
        workflow_version=WORKFLOW_VERSION,
        prompt_version="v1",
        model_name="gpt-5-mini",
        agent_versions={"listing_agent": "listing_agent:v1"},
        started_at=started_at,
        completed_at=started_at,
        total_duration_ms=0,
        agent_latencies_ms={"listing_agent": 0},
        traced=False,
    )
