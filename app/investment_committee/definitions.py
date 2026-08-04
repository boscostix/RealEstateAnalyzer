"""Agent definition for the investment-committee layer."""

from __future__ import annotations

from agents import Agent, ModelSettings

from app.investment_committee.context import CommitteeRunContext
from app.investment_committee.models import InvestmentCommitteeOutput
from app.investment_committee.prompts import INVESTMENT_COMMITTEE_PROMPT
from app.investment_committee.versioning_runtime import (
    COMMITTEE_AGENT_NAME,
    build_committee_agent_version,
    build_committee_prompt_version,
)


def build_investment_committee_agent(model: str) -> Agent[CommitteeRunContext]:
    """Create the single investment-committee agent with no tool access."""

    return Agent[CommitteeRunContext](
        name=COMMITTEE_AGENT_NAME,
        instructions=(
            f"{INVESTMENT_COMMITTEE_PROMPT.system_instructions} "
            "Return only the strict structured investment committee schema. "
            f"Agent version: {build_committee_agent_version()}. "
            f"Prompt version: {build_committee_prompt_version()}."
        ),
        output_type=InvestmentCommitteeOutput,
        model=model,
        model_settings=ModelSettings(),
        tools=[],
    )
