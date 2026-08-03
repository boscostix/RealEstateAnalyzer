"""API request and response models for the investment-committee workflow."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.agent_research.models import UnifiedAgentResearchPackage
from app.investment_committee.models import (
    CommitteeExecutionMetadata,
    CommitteeUsageMetadata,
    DecisionContext,
    InvestmentCommitteeOutput,
)
from app.models.assumptions import AnalysisAssumptions
from app.models.extraction import ErrorDetail
from app.models.underwriting import UnderwritingAnalysis
from app.models.verification import VerifiedPropertySnapshot


class CommitteeApiModel(BaseModel):
    """Strict base model for investment-committee API contracts."""

    model_config = ConfigDict(extra="forbid")


class InvestmentCommitteeAnalyzeRequest(CommitteeApiModel):
    """API payload used to execute one investment-committee analysis."""

    property: VerifiedPropertySnapshot
    assumptions: AnalysisAssumptions
    underwriting: UnderwritingAnalysis
    agent_research: UnifiedAgentResearchPackage
    decision_context: DecisionContext | None = None
    analysis_id: str | None = None


class InvestmentCommitteeAnalyzeResponse(CommitteeApiModel):
    """Response envelope for the complete investment-committee workflow."""

    success: bool
    committee_output: InvestmentCommitteeOutput | None = None
    execution_metadata: CommitteeExecutionMetadata | None = None
    usage_metadata: CommitteeUsageMetadata | None = None
    warnings: list[str] = Field(default_factory=list)
    error: ErrorDetail | None = None
