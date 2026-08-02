"""API request and response models for unified agent research runs."""

from __future__ import annotations

from pydantic import Field

from app.agent_research.models import AgentModel, UnifiedAgentResearchPackage
from app.models.extraction import PropertyExtractionResult
from app.models.research_package import ResearchPackage
from app.models.underwriting import UnderwritingAnalysis
from app.models.verification import VerifiedPropertySnapshot


class AgentResearchRunRequest(AgentModel):
    """API payload used to execute the full structured agent workflow."""

    verified_property: VerifiedPropertySnapshot
    listing_extraction: PropertyExtractionResult | None = None
    research_package: ResearchPackage | None = None
    underwriting_result: UnderwritingAnalysis | None = None
    analysis_id: str | None = None
    bypass_research_cache: bool = False


class AgentResearchRunResponse(AgentModel):
    """Response envelope for the complete agent-research workflow."""

    success: bool
    package: UnifiedAgentResearchPackage | None = None
    warnings: list[str] = Field(default_factory=list)
