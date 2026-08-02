"""Agent-specific input and output models for Phase 3 specialist agents."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import Field

from app.agent_research.models import AgentModel, AgentResearchOutput
from app.agent_research.tool_models import (
    FloodResearchPayload,
    ListingHistoryPayload,
    ListingSnapshotPayload,
    NeighborhoodSummaryPayload,
    PublicRecordsSummaryPayload,
    RentalCompsPayload,
    SalesCompsPayload,
    SchoolResearchPayload,
    TaxHistoryPayload,
    TransactionHistoryPayload,
    UnderwritingSummaryPayload,
)
from app.models.verification import VerifiedPropertySnapshot


class ListingAgentInput(AgentModel):
    property_key: str
    request_id: str
    analysis_id: str | None = None
    verified_property: VerifiedPropertySnapshot
    listing_snapshot: ListingSnapshotPayload
    listing_history: ListingHistoryPayload
    unresolved_verified_fields: list[str] = Field(default_factory=list)


class PublicRecordsAgentInput(AgentModel):
    property_key: str
    request_id: str
    analysis_id: str | None = None
    verified_property: VerifiedPropertySnapshot
    public_records_summary: PublicRecordsSummaryPayload
    tax_history: TaxHistoryPayload
    transaction_history: TransactionHistoryPayload


class ComparableAgentInput(AgentModel):
    property_key: str
    request_id: str
    analysis_id: str | None = None
    verified_property: VerifiedPropertySnapshot
    sales_comparables: SalesCompsPayload
    rental_comparables: RentalCompsPayload
    underwriting_summary: UnderwritingSummaryPayload | None = None


class NeighborhoodAgentInput(AgentModel):
    property_key: str
    request_id: str
    analysis_id: str | None = None
    verified_property: VerifiedPropertySnapshot
    neighborhood_summary: NeighborhoodSummaryPayload
    school_research: SchoolResearchPayload
    flood_research: FloodResearchPayload


class ListingAgentOutput(AgentResearchOutput):
    agent_name: Literal["listing_agent"]


class PublicRecordsAgentOutput(AgentResearchOutput):
    agent_name: Literal["public_records_agent"]


class ComparableAgentOutput(AgentResearchOutput):
    agent_name: Literal["comparable_agent"]


class NeighborhoodAgentOutput(AgentResearchOutput):
    agent_name: Literal["neighborhood_agent"]


class NeighborhoodGuardrailReport(AgentModel):
    blocked_terms: list[str] = Field(default_factory=list)
    blocked_phrases: list[str] = Field(default_factory=list)


class GuardrailReport(AgentModel):
    recommendation_phrases: list[str] = Field(default_factory=list)
    invalid_sources: list[str] = Field(default_factory=list)
    invalid_conflict_sources: list[str] = Field(default_factory=list)
    unsupported_material_findings: list[str] = Field(default_factory=list)
    neighborhood: NeighborhoodGuardrailReport | None = None
    maximum_confidence_applied: Decimal | None = None
