"""Typed runtime context shared by specialist agents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.agent_research.config import AgentRuntimeConfig
from app.models.extraction import PropertyExtractionResult
from app.models.research_package import ResearchPackage
from app.models.underwriting import UnderwritingAnalysis
from app.models.verification import VerifiedPropertySnapshot


@dataclass(slots=True)
class ResearchServiceContainer:
    """Container for deterministic services exposed to later tool wrappers."""

    listing_service: Any | None = None
    public_records_service: Any | None = None
    sales_comps_service: Any | None = None
    rental_comps_service: Any | None = None
    neighborhood_service: Any | None = None
    underwriting_service: Any | None = None


@dataclass(slots=True)
class AgentRunContext:
    """Per-run context passed to the OpenAI Agents SDK."""

    request_id: str
    analysis_id: str | None
    verified_property: VerifiedPropertySnapshot
    listing_extraction: PropertyExtractionResult | None
    underwriting_result: UnderwritingAnalysis | None
    research_package: ResearchPackage
    research_services: ResearchServiceContainer
    agent_config: AgentRuntimeConfig
