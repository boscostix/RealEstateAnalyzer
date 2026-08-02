"""Skeletal specialist-agent definitions with strict structured outputs."""

from __future__ import annotations

from dataclasses import dataclass

from agents import Agent, ModelSettings

from app.agent_research.context import AgentRunContext
from app.agent_research.guardrails import guardrails_for_agent
from app.agent_research.models import AgentResearchOutput
from app.agent_research.prompts import prompt_for_agent
from app.agent_research.risk_models import PropertyRiskAgentOutput
from app.agent_research.specialist_models import (
    ComparableAgentOutput,
    ListingAgentOutput,
    NeighborhoodAgentOutput,
    PublicRecordsAgentOutput,
)
from app.agent_research.tools import tools_for_agent
from app.agent_research.versioning import (
    AgentName,
    build_agent_version,
)


@dataclass(frozen=True, slots=True)
class AgentDefinition:
    """Deterministic metadata used to construct one specialist agent."""

    name: AgentName
    role: str
    instruction: str


AGENT_DEFINITIONS: tuple[AgentDefinition, ...] = (
    AgentDefinition(
        name=AgentName.LISTING,
        role="Interpret verified listing information and listing-origin claims.",
        instruction=(
            "Use only the verified property and provided listing research. "
            "Identify important listing claims, contradictions, missing information, "
            "and due-diligence questions. Do not invent facts, sources, repairs, "
            "investment recommendations, or inspection conclusions."
        ),
    ),
    AgentDefinition(
        name=AgentName.PUBLIC_RECORDS,
        role="Interpret public-record data and compare it against the listing.",
        instruction=(
            "Use only deterministic public-record research and the verified property. "
            "Highlight disagreements, tax or assessment trends, permit-history gaps, "
            "and follow-up questions. Do not provide legal conclusions or invent "
            "missing records."
        ),
    ),
    AgentDefinition(
        name=AgentName.COMPARABLE,
        role="Interpret sales and rental comparable evidence.",
        instruction=(
            "Use only deterministic comparable outputs and underwriting assumptions "
            "provided in context. Explain comparable relevance, outliers, and dataset "
            "weaknesses. Do not invent adjustments, comparables, or appraisals."
        ),
    ),
    AgentDefinition(
        name=AgentName.NEIGHBORHOOD,
        role="Interpret neighborhood datasets without generating recommendations.",
        instruction=(
            "Use only deterministic neighborhood data. Identify relevant context, "
            "gaps, and follow-up questions while avoiding protected-class inferences "
            "or fair-housing sensitive conclusions."
        ),
    ),
    AgentDefinition(
        name=AgentName.PROPERTY_RISK,
        role="Interpret property-level risks using deterministic evidence.",
        instruction=(
            "Use only verified property data, research-package evidence, and "
            "underwriting outputs already supplied. Highlight supported risks, "
            "conflicts, and missing due diligence. Do not claim to perform an "
            "inspection, appraisal, or final investment decision."
        ),
    ),
)


def build_specialist_agents(config_model: str) -> dict[AgentName, Agent[AgentRunContext]]:
    """Create the specialist agents used by later orchestration phases."""

    output_types: dict[AgentName, type[AgentResearchOutput]] = {
        AgentName.LISTING: ListingAgentOutput,
        AgentName.PUBLIC_RECORDS: PublicRecordsAgentOutput,
        AgentName.COMPARABLE: ComparableAgentOutput,
        AgentName.NEIGHBORHOOD: NeighborhoodAgentOutput,
        AgentName.PROPERTY_RISK: PropertyRiskAgentOutput,
    }
    agents: dict[AgentName, Agent[AgentRunContext]] = {}
    for definition in AGENT_DEFINITIONS:
        prompt = prompt_for_agent(definition.name)
        agents[definition.name] = Agent[AgentRunContext](
            name=definition.name,
            instructions=(
                f"{definition.instruction} "
                f"{prompt.system_instructions} "
                f"Return only the strict structured output schema for this agent. "
                f"Agent version: {build_agent_version(definition.name)}. "
                f"Prompt version: {prompt.prompt_version}."
            ),
            output_type=output_types[definition.name],
            model=config_model,
            model_settings=ModelSettings(temperature=0),
            tools=list(tools_for_agent(definition.name)),
            output_guardrails=guardrails_for_agent(definition.name),
        )
    return agents


__all__ = ["AGENT_DEFINITIONS", "build_specialist_agents"]
