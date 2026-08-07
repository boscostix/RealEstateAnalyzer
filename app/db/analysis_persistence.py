"""Helpers for analysis persistence, deserialization, and status rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.agent_research.models import UnifiedAgentResearchPackage
from app.db.models import AnalysisRecord, AnalysisStage, AnalysisStatus, PropertyRecord
from app.db.snapshots import (
    deserialize_mapping_snapshot,
    deserialize_model_snapshot,
    snapshot_schema_version,
)
from app.exceptions import AnalysisImmutableError, InvalidAnalysisStateError
from app.investment_committee.models import InvestmentCommitteeOutput
from app.models.assumptions import AnalysisAssumptions
from app.models.property import NormalizedProperty
from app.models.research_package import ResearchPackage
from app.models.underwriting import UnderwritingAnalysis
from app.models.verification import VerifiedPropertySnapshot

ALLOWED_ANALYSIS_STATUS_TRANSITIONS: dict[AnalysisStatus, set[AnalysisStatus]] = {
    AnalysisStatus.PENDING: {AnalysisStatus.RUNNING},
    AnalysisStatus.RUNNING: {AnalysisStatus.COMPLETED, AnalysisStatus.FAILED},
    AnalysisStatus.COMPLETED: set(),
    AnalysisStatus.FAILED: set(),
}


@dataclass(frozen=True)
class PersistedAnalysisData:
    """Deserialized analysis snapshots and result payloads."""

    property_snapshot: VerifiedPropertySnapshot | None
    assumptions_snapshot: AnalysisAssumptions | None
    underwriting_result: UnderwritingAnalysis | None
    research_result: ResearchPackage | None
    agent_research_result: UnifiedAgentResearchPackage | None
    investment_committee_result: InvestmentCommitteeOutput | None
    execution_metadata: dict[str, Any] | None
    property_schema_version: str | None
    assumptions_schema_version: str | None
    underwriting_schema_version: str | None
    research_schema_version: str | None
    agent_research_schema_version: str | None
    investment_committee_schema_version: str | None
    execution_schema_version: str | None


def validate_status_transition(current: AnalysisStatus, target: AnalysisStatus) -> None:
    """Validate one analysis lifecycle transition."""

    if current == target:
        return
    allowed_targets = ALLOWED_ANALYSIS_STATUS_TRANSITIONS[current]
    if target not in allowed_targets:
        raise InvalidAnalysisStateError(
            message=(f"Invalid analysis status transition from {current.value} to {target.value}.")
        )


def ensure_analysis_mutable(analysis: AnalysisRecord) -> None:
    """Reject mutations once an analysis has completed."""

    if analysis.status == AnalysisStatus.COMPLETED:
        raise AnalysisImmutableError()


def deserialize_property_record(
    property_record: PropertyRecord,
) -> tuple[NormalizedProperty | None, VerifiedPropertySnapshot | None]:
    """Deserialize the current normalized and verified property snapshots."""

    normalized = deserialize_model_snapshot(
        property_record.normalized_property_json,
        NormalizedProperty,
    )
    verified = deserialize_model_snapshot(
        property_record.verified_property_json,
        VerifiedPropertySnapshot,
    )
    return normalized, verified


def deserialize_analysis_record(analysis: AnalysisRecord) -> PersistedAnalysisData:
    """Deserialize all persisted analysis snapshots and result payloads."""

    return PersistedAnalysisData(
        property_snapshot=deserialize_model_snapshot(
            analysis.property_snapshot_json,
            VerifiedPropertySnapshot,
        ),
        assumptions_snapshot=deserialize_model_snapshot(
            analysis.assumptions_snapshot_json,
            AnalysisAssumptions,
        ),
        underwriting_result=deserialize_model_snapshot(
            analysis.underwriting_result_json,
            UnderwritingAnalysis,
        ),
        research_result=deserialize_model_snapshot(
            analysis.research_result_json,
            ResearchPackage,
        ),
        agent_research_result=deserialize_model_snapshot(
            analysis.agent_research_result_json,
            UnifiedAgentResearchPackage,
        ),
        investment_committee_result=deserialize_model_snapshot(
            analysis.investment_committee_result_json,
            InvestmentCommitteeOutput,
        ),
        execution_metadata=deserialize_mapping_snapshot(analysis.execution_metadata_json),
        property_schema_version=snapshot_schema_version(analysis.property_snapshot_json),
        assumptions_schema_version=snapshot_schema_version(analysis.assumptions_snapshot_json),
        underwriting_schema_version=snapshot_schema_version(analysis.underwriting_result_json),
        research_schema_version=snapshot_schema_version(analysis.research_result_json),
        agent_research_schema_version=snapshot_schema_version(analysis.agent_research_result_json),
        investment_committee_schema_version=snapshot_schema_version(
            analysis.investment_committee_result_json
        ),
        execution_schema_version=snapshot_schema_version(analysis.execution_metadata_json),
    )


def stage_allows_status(stage: AnalysisStage | None, status: AnalysisStatus) -> bool:
    """Provide a lightweight consistency check between stage and status."""

    if status == AnalysisStatus.PENDING:
        return stage in {None, AnalysisStage.PREPARATION}
    if status == AnalysisStatus.RUNNING:
        return True
    if status in {AnalysisStatus.COMPLETED, AnalysisStatus.FAILED}:
        return True
    return False
