"""Focused repository for persisted analyses and lifecycle rules."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.agent_research.models import UnifiedAgentResearchPackage
from app.db.analysis_persistence import ensure_analysis_mutable, validate_status_transition
from app.db.models import AnalysisRecord, AnalysisStage, AnalysisStatus
from app.db.snapshots import (
    SNAPSHOT_SCHEMA_VERSION_V1,
    serialize_mapping_snapshot,
    serialize_model_snapshot,
)
from app.exceptions import (
    AnalysisNotFoundError,
    AnalysisVersionConflictError,
    DatabaseOperationError,
)
from app.investment_committee.models import InvestmentCommitteeOutput
from app.models.assumptions import AnalysisAssumptions
from app.models.research_package import ResearchPackage
from app.models.underwriting import UnderwritingAnalysis
from app.models.verification import VerifiedPropertySnapshot


class AnalysisRepository:
    """Persistence operations for analysis history and status changes."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        *,
        property_id: str,
        property_snapshot: VerifiedPropertySnapshot | None = None,
        assumptions_snapshot: AnalysisAssumptions | None = None,
        parent_analysis_id: str | None = None,
        version: int | None = None,
    ) -> AnalysisRecord:
        next_version = version if version is not None else self.get_next_version(property_id)
        analysis = AnalysisRecord(
            property_id=property_id,
            parent_analysis_id=parent_analysis_id,
            version=next_version,
            status=AnalysisStatus.PENDING,
            current_stage=AnalysisStage.PREPARATION,
            property_snapshot_json=(
                None if property_snapshot is None else serialize_model_snapshot(property_snapshot)
            ),
            assumptions_snapshot_json=(
                None
                if assumptions_snapshot is None
                else serialize_model_snapshot(assumptions_snapshot)
            ),
            analysis_schema_version=SNAPSHOT_SCHEMA_VERSION_V1,
            report_schema_version=SNAPSHOT_SCHEMA_VERSION_V1,
        )
        self.session.add(analysis)
        self._commit_refresh(analysis)
        return analysis

    def get_by_id(self, analysis_id: str) -> AnalysisRecord | None:
        return self.session.get(AnalysisRecord, analysis_id)

    def get_required_by_id(self, analysis_id: str) -> AnalysisRecord:
        analysis = self.get_by_id(analysis_id)
        if analysis is None:
            raise AnalysisNotFoundError()
        return analysis

    def list_for_property(self, property_id: str) -> list[AnalysisRecord]:
        statement = (
            select(AnalysisRecord)
            .where(AnalysisRecord.property_id == property_id)
            .order_by(AnalysisRecord.version.desc())
        )
        return list(self.session.scalars(statement))

    def get_latest_for_property(self, property_id: str) -> AnalysisRecord | None:
        statement = (
            select(AnalysisRecord)
            .where(AnalysisRecord.property_id == property_id)
            .order_by(AnalysisRecord.version.desc())
            .limit(1)
        )
        return self.session.scalars(statement).first()

    def count_for_property(self, property_id: str) -> int:
        statement = select(func.count()).where(AnalysisRecord.property_id == property_id)
        count = self.session.scalar(statement)
        return 0 if count is None else int(count)

    def get_next_version(self, property_id: str) -> int:
        statement = select(func.max(AnalysisRecord.version)).where(
            AnalysisRecord.property_id == property_id
        )
        max_version = self.session.scalar(statement)
        return 1 if max_version is None else int(max_version) + 1

    def update_status(
        self,
        analysis_id: str,
        *,
        status: AnalysisStatus,
        current_stage: AnalysisStage | None = None,
        failure_stage: AnalysisStage | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> AnalysisRecord:
        analysis = self.get_required_by_id(analysis_id)
        validate_status_transition(analysis.status, status)
        analysis.status = status

        now = datetime.now(UTC)
        if status == AnalysisStatus.RUNNING:
            analysis.started_at = analysis.started_at or now
        if status == AnalysisStatus.COMPLETED:
            analysis.completed_at = now
        if status == AnalysisStatus.FAILED:
            analysis.failed_at = now
            analysis.failure_stage = failure_stage
            analysis.error_code = error_code
            analysis.error_message = error_message
        if current_stage is not None:
            analysis.current_stage = current_stage

        self._commit_refresh(analysis)
        return analysis

    def update_results(
        self,
        analysis_id: str,
        *,
        property_snapshot: VerifiedPropertySnapshot | None = None,
        assumptions_snapshot: AnalysisAssumptions | None = None,
        underwriting_result: UnderwritingAnalysis | None = None,
        research_result: ResearchPackage | None = None,
        agent_research_result: UnifiedAgentResearchPackage | None = None,
        investment_committee_result: InvestmentCommitteeOutput | None = None,
        execution_metadata: dict[str, Any] | None = None,
        current_stage: AnalysisStage | None = None,
    ) -> AnalysisRecord:
        analysis = self.get_required_by_id(analysis_id)
        ensure_analysis_mutable(analysis)
        if property_snapshot is not None:
            analysis.property_snapshot_json = serialize_model_snapshot(property_snapshot)
        if assumptions_snapshot is not None:
            analysis.assumptions_snapshot_json = serialize_model_snapshot(assumptions_snapshot)
        if underwriting_result is not None:
            analysis.underwriting_result_json = serialize_model_snapshot(underwriting_result)
        if research_result is not None:
            analysis.research_result_json = serialize_model_snapshot(research_result)
        if agent_research_result is not None:
            analysis.agent_research_result_json = serialize_model_snapshot(agent_research_result)
        if investment_committee_result is not None:
            analysis.investment_committee_result_json = serialize_model_snapshot(
                investment_committee_result
            )
        if execution_metadata is not None:
            analysis.execution_metadata_json = serialize_mapping_snapshot(execution_metadata)
        if current_stage is not None:
            analysis.current_stage = current_stage
        self._commit_refresh(analysis)
        return analysis

    def _commit_refresh(self, analysis: AnalysisRecord) -> None:
        try:
            self.session.commit()
            self.session.refresh(analysis)
        except IntegrityError as exc:
            self.session.rollback()
            raise AnalysisVersionConflictError() from exc
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise DatabaseOperationError(message="Failed to persist analysis state.") from exc
