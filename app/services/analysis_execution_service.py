"""Persisted analysis execution orchestration for Milestone 6."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable, Coroutine
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any, Protocol

from sqlalchemy.orm import Session
from sqlalchemy.orm.session import sessionmaker

from app.agent_research.api_models import AgentResearchRunRequest
from app.agent_research.synthesis import UnifiedSynthesisService
from app.db.analysis_persistence import deserialize_analysis_record
from app.db.models import AnalysisStage, AnalysisStatus
from app.db.repositories import AnalysisRepository
from app.db.session import SessionLocal
from app.exceptions import AppError, SnapshotValidationError
from app.investment_committee.models import DecisionContext, InvestmentCommitteeInput
from app.investment_committee.services import InvestmentCommitteeService
from app.logging import logger
from app.models.assumptions import RunAnalysisRequest
from app.models.research_package import ResearchPackageRequest, ResearchPackageResponse
from app.models.underwriting import RunAnalysisResponse
from app.services.research_orchestrator import ResearchOrchestrator
from app.services.underwriting_service import UnderwritingService


class ResearchOrchestratorProtocol(Protocol):
    async def research(self, request: ResearchPackageRequest) -> ResearchPackageResponse: ...


class SynthesisServiceProtocol(Protocol):
    async def run(
        self,
        *,
        request_id: str,
        payload: AgentResearchRunRequest,
    ) -> Any: ...


class CommitteeServiceProtocol(Protocol):
    async def analyze_with_details(
        self,
        *,
        request_id: str,
        committee_input: InvestmentCommitteeInput,
        analysis_id: str | None = None,
    ) -> Any: ...


class InProcessAnalysisTaskRunner:
    """Simple in-process task scheduler for non-durable demo execution."""

    def __init__(
        self,
        *,
        scheduler: Callable[[Coroutine[Any, Any, None]], asyncio.Task[None]] | None = None,
    ) -> None:
        self._scheduler = scheduler or asyncio.create_task
        self._tasks: dict[str, asyncio.Task[None]] = {}

    def start(
        self,
        *,
        analysis_id: str,
        coroutine: Coroutine[Any, Any, None],
    ) -> asyncio.Task[None]:
        task = self._scheduler(coroutine)
        self._tasks[analysis_id] = task
        task.add_done_callback(lambda _: self._tasks.pop(analysis_id, None))
        return task

    def get(self, analysis_id: str) -> asyncio.Task[None] | None:
        return self._tasks.get(analysis_id)


class AnalysisExecutionService:
    """Runs a persisted analysis through underwriting, research, agents, and committee."""

    def __init__(
        self,
        *,
        session_factory: sessionmaker[Session] | Callable[[], Session] = SessionLocal,
        underwriting_service: UnderwritingService | None = None,
        research_orchestrator: ResearchOrchestratorProtocol | None = None,
        synthesis_service: SynthesisServiceProtocol | None = None,
        committee_service: CommitteeServiceProtocol | None = None,
        task_runner: InProcessAnalysisTaskRunner | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._underwriting_service = underwriting_service or UnderwritingService()
        resolved_research_orchestrator = research_orchestrator or ResearchOrchestrator()
        self._research_orchestrator = resolved_research_orchestrator
        self._synthesis_service: SynthesisServiceProtocol
        if synthesis_service is None:
            self._synthesis_service = UnifiedSynthesisService(
                research_orchestrator=(
                    resolved_research_orchestrator
                    if isinstance(resolved_research_orchestrator, ResearchOrchestrator)
                    else None
                )
            )
        else:
            self._synthesis_service = synthesis_service
        self._committee_service = committee_service or InvestmentCommitteeService()
        self._task_runner = task_runner or InProcessAnalysisTaskRunner()

    def start_background_analysis(
        self,
        *,
        analysis_id: str,
        request_id: str,
    ) -> asyncio.Task[None]:
        """Schedule analysis execution in-process and return the created task."""

        return self._task_runner.start(
            analysis_id=analysis_id,
            coroutine=self.run_analysis(analysis_id=analysis_id, request_id=request_id),
        )

    async def run_analysis(
        self,
        *,
        analysis_id: str,
        request_id: str,
    ) -> None:
        """Execute the full persisted analysis pipeline."""

        started_at = datetime.now(UTC)
        started_perf = time.perf_counter()
        execution_metadata = self._build_execution_metadata(
            analysis_id=analysis_id,
            request_id=request_id,
            started_at=started_at,
        )
        current_stage = AnalysisStage.PREPARATION

        self._update_running_state(
            analysis_id=analysis_id,
            stage=current_stage,
            execution_metadata=execution_metadata,
            transition_to_running=True,
        )
        try:
            inputs = self._load_analysis_inputs(analysis_id)

            current_stage = AnalysisStage.UNDERWRITING
            self._update_running_state(
                analysis_id=analysis_id,
                stage=current_stage,
                execution_metadata=execution_metadata,
            )
            underwriting_response: RunAnalysisResponse = self._underwriting_service.run(
                RunAnalysisRequest(
                    property=inputs["property_snapshot"],
                    assumptions=inputs["assumptions_snapshot"],
                )
            )
            if underwriting_response.analysis is None or underwriting_response.metadata is None:
                raise SnapshotValidationError(
                    message="Underwriting did not return a complete result."
                )
            execution_metadata["versions"]["calculation_version"] = (
                underwriting_response.metadata.calculation_version
            )
            self._persist_partial_results(
                analysis_id=analysis_id,
                stage=current_stage,
                execution_metadata=execution_metadata,
                underwriting_result=underwriting_response.analysis,
            )

            current_stage = AnalysisStage.RESEARCH
            self._update_running_state(
                analysis_id=analysis_id,
                stage=current_stage,
                execution_metadata=execution_metadata,
            )
            research_response = await self._research_orchestrator.research(
                ResearchPackageRequest(property=inputs["property_snapshot"])
            )
            if research_response.package is None:
                raise SnapshotValidationError(message="Research did not return a package.")
            self._persist_partial_results(
                analysis_id=analysis_id,
                stage=current_stage,
                execution_metadata=execution_metadata,
                underwriting_result=underwriting_response.analysis,
                research_result=research_response.package,
            )

            current_stage = AnalysisStage.AGENT_RESEARCH
            self._update_running_state(
                analysis_id=analysis_id,
                stage=current_stage,
                execution_metadata=execution_metadata,
            )
            agent_response = await self._synthesis_service.run(
                request_id=request_id,
                payload=AgentResearchRunRequest(
                    verified_property=inputs["property_snapshot"],
                    research_package=research_response.package,
                    underwriting_result=underwriting_response.analysis,
                    analysis_id=analysis_id,
                ),
            )
            if agent_response.package is None:
                raise SnapshotValidationError(message="Agent research did not return a package.")
            execution_metadata["versions"]["agent_workflow_version"] = (
                agent_response.package.execution_metadata.workflow_version
            )
            execution_metadata["versions"]["agent_prompt_version"] = (
                agent_response.package.execution_metadata.prompt_version
            )
            self._persist_partial_results(
                analysis_id=analysis_id,
                stage=current_stage,
                execution_metadata=execution_metadata,
                underwriting_result=underwriting_response.analysis,
                research_result=research_response.package,
                agent_research_result=agent_response.package,
            )

            current_stage = AnalysisStage.INVESTMENT_COMMITTEE
            self._update_running_state(
                analysis_id=analysis_id,
                stage=current_stage,
                execution_metadata=execution_metadata,
            )
            committee_result = await self._committee_service.analyze_with_details(
                request_id=request_id,
                committee_input=InvestmentCommitteeInput(
                    property=inputs["property_snapshot"],
                    assumptions=inputs["assumptions_snapshot"],
                    underwriting=underwriting_response.analysis,
                    agent_research=agent_response.package,
                    decision_context=inputs["decision_context"],
                ),
                analysis_id=analysis_id,
            )
            execution_metadata["versions"]["committee_agent_version"] = (
                committee_result.execution_metadata.agent_version
            )
            execution_metadata["versions"]["committee_prompt_version"] = (
                committee_result.execution_metadata.prompt_version
            )
            execution_metadata["warnings"] = list(committee_result.warnings)

            final_stage = AnalysisStage.PERSISTENCE
            execution_metadata["status"] = AnalysisStatus.COMPLETED.value
            execution_metadata["current_stage"] = final_stage.value
            execution_metadata["completed_at"] = datetime.now(UTC).isoformat()
            execution_metadata["total_duration_ms"] = int(
                (time.perf_counter() - started_perf) * 1000
            )
            self._persist_partial_results(
                analysis_id=analysis_id,
                stage=final_stage,
                execution_metadata=execution_metadata,
                underwriting_result=underwriting_response.analysis,
                research_result=research_response.package,
                agent_research_result=agent_response.package,
                investment_committee_result=committee_result.output,
            )
            self._update_completed_state(analysis_id=analysis_id, stage=final_stage)
        except Exception as exc:
            self._handle_failure(
                analysis_id=analysis_id,
                stage=current_stage,
                execution_metadata=execution_metadata,
                started_perf=started_perf,
                error=exc,
            )
            raise

    def _load_analysis_inputs(self, analysis_id: str) -> dict[str, Any]:
        with self._session() as session:
            analysis = AnalysisRepository(session).get_required_by_id(analysis_id)
            persisted = deserialize_analysis_record(analysis)
        if persisted.property_snapshot is None:
            raise SnapshotValidationError(
                message="Analysis is missing a verified property snapshot."
            )
        if persisted.assumptions_snapshot is None:
            raise SnapshotValidationError(message="Analysis is missing an assumptions snapshot.")
        decision_context = None
        if persisted.execution_metadata is not None:
            decision_context_payload = persisted.execution_metadata.get("inputs", {}).get(
                "decision_context"
            )
            if decision_context_payload is not None:
                decision_context = DecisionContext.model_validate(decision_context_payload)
        return {
            "property_snapshot": persisted.property_snapshot,
            "assumptions_snapshot": persisted.assumptions_snapshot,
            "decision_context": decision_context,
        }

    def _update_running_state(
        self,
        *,
        analysis_id: str,
        stage: AnalysisStage,
        execution_metadata: dict[str, Any],
        transition_to_running: bool = False,
    ) -> None:
        execution_metadata["current_stage"] = stage.value
        execution_metadata["stage_history"].append(
            {
                "stage": stage.value,
                "entered_at": datetime.now(UTC).isoformat(),
            }
        )
        with self._session() as session:
            repository = AnalysisRepository(session)
            if transition_to_running:
                repository.update_status(
                    analysis_id,
                    status=AnalysisStatus.RUNNING,
                    current_stage=stage,
                )
            repository.update_results(
                analysis_id,
                current_stage=stage,
                execution_metadata=execution_metadata,
            )

    def _persist_partial_results(
        self,
        *,
        analysis_id: str,
        stage: AnalysisStage,
        execution_metadata: dict[str, Any],
        underwriting_result: Any | None = None,
        research_result: Any | None = None,
        agent_research_result: Any | None = None,
        investment_committee_result: Any | None = None,
    ) -> None:
        execution_metadata["current_stage"] = stage.value
        with self._session() as session:
            AnalysisRepository(session).update_results(
                analysis_id,
                underwriting_result=underwriting_result,
                research_result=research_result,
                agent_research_result=agent_research_result,
                investment_committee_result=investment_committee_result,
                execution_metadata=execution_metadata,
                current_stage=stage,
            )

    def _update_completed_state(self, *, analysis_id: str, stage: AnalysisStage) -> None:
        with self._session() as session:
            AnalysisRepository(session).update_status(
                analysis_id,
                status=AnalysisStatus.COMPLETED,
                current_stage=stage,
            )

    def _handle_failure(
        self,
        *,
        analysis_id: str,
        stage: AnalysisStage,
        execution_metadata: dict[str, Any],
        started_perf: float,
        error: Exception,
    ) -> None:
        error_code, error_message = self._safe_error_details(error)
        execution_metadata["status"] = AnalysisStatus.FAILED.value
        execution_metadata["current_stage"] = stage.value
        execution_metadata["failed_at"] = datetime.now(UTC).isoformat()
        execution_metadata["failure"] = {
            "stage": stage.value,
            "error_code": error_code,
            "error_message": error_message,
        }
        execution_metadata["total_duration_ms"] = int((time.perf_counter() - started_perf) * 1000)
        logger.exception(
            "analysis_execution_failed analysis_id=%s stage=%s error_code=%s",
            analysis_id,
            stage.value,
            error_code,
            exc_info=error,
        )
        with self._session() as session:
            repository = AnalysisRepository(session)
            repository.update_results(
                analysis_id,
                execution_metadata=execution_metadata,
                current_stage=stage,
            )
            repository.update_status(
                analysis_id,
                status=AnalysisStatus.FAILED,
                current_stage=stage,
                failure_stage=stage,
                error_code=error_code,
                error_message=error_message,
            )

    def _build_execution_metadata(
        self,
        *,
        analysis_id: str,
        request_id: str,
        started_at: datetime,
    ) -> dict[str, Any]:
        return {
            "request_id": request_id,
            "analysis_id": analysis_id,
            "status": AnalysisStatus.PENDING.value,
            "current_stage": AnalysisStage.PREPARATION.value,
            "started_at": started_at.isoformat(),
            "completed_at": None,
            "failed_at": None,
            "total_duration_ms": 0,
            "stage_history": [],
            "versions": {},
            "warnings": [],
            "failure": None,
        }

    def _safe_error_details(self, error: Exception) -> tuple[str, str]:
        if isinstance(error, AppError):
            return error.code, error.message
        return "analysis_execution_failed", "Analysis execution failed."

    @contextmanager
    def _session(self) -> Any:
        session = self._session_factory()
        try:
            yield session
        finally:
            session.close()
