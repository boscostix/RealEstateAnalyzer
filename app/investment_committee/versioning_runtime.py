"""Runtime version labels for the investment-committee agent."""

from __future__ import annotations

from app.investment_committee.versioning import (
    COMMITTEE_AGENT_VERSION,
    COMMITTEE_PROMPT_VERSION,
)

COMMITTEE_AGENT_NAME = "investment_committee_agent"


def build_committee_agent_version() -> str:
    return f"{COMMITTEE_AGENT_NAME}:{COMMITTEE_AGENT_VERSION}"


def build_committee_prompt_version() -> str:
    return f"{COMMITTEE_AGENT_NAME}:{COMMITTEE_PROMPT_VERSION}"
