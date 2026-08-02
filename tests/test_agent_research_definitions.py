"""Tests for skeletal specialist-agent definitions."""

from __future__ import annotations

from app.agent_research.definitions import AGENT_DEFINITIONS, build_specialist_agents
from app.agent_research.models import AgentResearchOutput
from app.agent_research.versioning import AgentName


def test_build_specialist_agents_returns_all_expected_agents() -> None:
    agents = build_specialist_agents("gpt-5-mini")

    assert set(agents) == {
        AgentName.LISTING,
        AgentName.PUBLIC_RECORDS,
        AgentName.COMPARABLE,
        AgentName.NEIGHBORHOOD,
        AgentName.PROPERTY_RISK,
    }
    for agent in agents.values():
        assert agent.output_type is AgentResearchOutput
        assert agent.model == "gpt-5-mini"


def test_agent_definitions_include_prompt_safety_language() -> None:
    listing_definition = next(
        definition for definition in AGENT_DEFINITIONS if definition.name == AgentName.LISTING
    )

    assert "Do not invent facts" in listing_definition.instruction
