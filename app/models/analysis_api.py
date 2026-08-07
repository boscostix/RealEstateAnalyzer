"""Frontend-oriented DTOs for persisted analysis APIs."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from app.agent_research.models import UnifiedAgentResearchPackage
from app.investment_committee.models import DecisionContext, InvestmentCommitteeOutput
from app.models.assumptions import AnalysisAssumptions
from app.models.property_api import AnalysisSummaryResponse, PropertyApiModel
from app.models.research_package import ResearchPackage
from app.models.underwriting import UnderwritingAnalysis
from app.models.verification import VerifiedPropertySnapshot


class AnalysisCreateRequest(PropertyApiModel):
    assumptions: AnalysisAssumptions
    decision_context: DecisionContext | None = None


class AnalysisDetail(PropertyApiModel):
    id: str
    property_id: str
    version: int
    status: str
    current_stage: str | None = None
    parent_analysis_id: str | None = None
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None
    failed_at: str | None = None
    failure_stage: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    property_snapshot: VerifiedPropertySnapshot | None = None
    assumptions: AnalysisAssumptions | None = None
    underwriting: UnderwritingAnalysis | None = None
    research: ResearchPackage | None = None
    agent_research: UnifiedAgentResearchPackage | None = None
    investment_committee: InvestmentCommitteeOutput | None = None
    execution: dict[str, Any] | None = None


class AnalysisCreateResponse(PropertyApiModel):
    success: bool
    analysis: AnalysisSummaryResponse


class AnalysisDetailResponse(PropertyApiModel):
    success: bool
    analysis: AnalysisDetail


class AnalysisListResponse(PropertyApiModel):
    success: bool
    analyses: list[AnalysisSummaryResponse] = Field(default_factory=list)
