"""Tests for versioned specialist-agent prompts."""

from __future__ import annotations

from app.agent_research.prompts import prompt_for_agent
from app.agent_research.versioning import AgentName


def test_prompts_are_versioned_and_focused() -> None:
    prompt = prompt_for_agent(AgentName.LISTING)

    assert prompt.prompt_version == "v1"
    assert "Do not invent facts" in prompt.system_instructions
    assert "buy, negotiate, pass" in prompt.system_instructions


def test_neighborhood_prompt_contains_fair_housing_restrictions() -> None:
    prompt = prompt_for_agent(AgentName.NEIGHBORHOOD)

    assert "protected characteristics" in prompt.system_instructions
    assert "Do not recommend where a person should or should not live" in prompt.system_instructions
