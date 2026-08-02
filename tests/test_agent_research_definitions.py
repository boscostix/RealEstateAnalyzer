"""Tests for skeletal specialist-agent definitions."""

from __future__ import annotations

from app.agent_research.definitions import AGENT_DEFINITIONS, build_specialist_agents
from app.agent_research.specialist_models import (
    ComparableAgentOutput,
    ListingAgentOutput,
    NeighborhoodAgentOutput,
    PublicRecordsAgentOutput,
)
from app.agent_research.tools import tools_for_agent
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
    assert agents[AgentName.LISTING].output_type is ListingAgentOutput
    assert agents[AgentName.PUBLIC_RECORDS].output_type is PublicRecordsAgentOutput
    assert agents[AgentName.COMPARABLE].output_type is ComparableAgentOutput
    assert agents[AgentName.NEIGHBORHOOD].output_type is NeighborhoodAgentOutput
    for name, agent in agents.items():
        assert agent.model == "gpt-5-mini"
        assert len(agent.tools) >= 1
        if name != AgentName.PROPERTY_RISK:
            assert len(agent.output_guardrails) >= 1


def test_agent_definitions_include_prompt_safety_language() -> None:
    listing_definition = next(
        definition for definition in AGENT_DEFINITIONS if definition.name == AgentName.LISTING
    )

    assert "Do not invent facts" in listing_definition.instruction


def test_tools_for_agent_returns_curated_tool_sets() -> None:
    assert len(tools_for_agent(AgentName.LISTING)) == 3
    assert len(tools_for_agent(AgentName.PUBLIC_RECORDS)) == 4
    assert len(tools_for_agent(AgentName.COMPARABLE)) == 3
