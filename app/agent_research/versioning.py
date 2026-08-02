"""Versioning constants and helpers for structured agent prompts."""

from __future__ import annotations

from enum import StrEnum


class AgentName(StrEnum):
    """Supported specialist agents for milestone-four orchestration."""

    LISTING = "listing_agent"
    PUBLIC_RECORDS = "public_records_agent"
    COMPARABLE = "comparable_agent"
    NEIGHBORHOOD = "neighborhood_agent"
    PROPERTY_RISK = "property_risk_agent"
    RESEARCH_ORCHESTRATOR = "research_orchestrator"


AGENT_VERSION = "v1"
PROMPT_VERSION = "v1"
WORKFLOW_VERSION = "v1"
WORKFLOW_NAME = "real_estate_agent_research"


def build_agent_version(agent_name: AgentName) -> str:
    """Return the stable version label for a specific agent."""

    return f"{agent_name}:{AGENT_VERSION}"


def build_prompt_version(agent_name: AgentName) -> str:
    """Return the stable prompt version label for a specific agent."""

    return f"{agent_name}:{PROMPT_VERSION}"
