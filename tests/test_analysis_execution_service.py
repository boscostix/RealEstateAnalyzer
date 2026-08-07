"""Tests for persisted analysis execution orchestration."""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.agent_research.api_models import AgentResearchRunResponse
from app.db.analysis_persistence import deserialize_analysis_record
from app.db.base import Base
from app.db.models import AnalysisStage, AnalysisStatus
from app.db.repositories import AnalysisRepository, PropertyRepository
from app.db.session import create_engine_from_url, create_session_factory
from app.exceptions import AppError
from app.investment_committee.models import (
    CommitteeExecutionMetadata,
    CommitteeUsageMetadata,
    InvestmentCommitteeAnalysisResult,
)
from app.models.research_package import ResearchPackageRequest, ResearchPackageResponse
from app.services.analysis_execution_service import (
    AnalysisExecutionService,
    InProcessAnalysisTaskRunner,
)
from app.services.underwriting_service import UnderwritingService
from tests.db.factories import (
    build_agent_research_package,
    build_assumptions,
    build_committee_output,
    build_research_package,
    build_verified_property,
)


@pytest.fixture
def db_session(tmp_path: Path) -> Generator[Session, None, None]:
    database_path = tmp_path / "analysis_execution.db"
    engine = create_engine_from_url(f"sqlite+pysqlite:///{database_path}")
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


class StubResearchOrchestrator:
    async def research(self, request: ResearchPackageRequest) -> ResearchPackageResponse:
        property_snapshot = request.property
        return ResearchPackageResponse(
            success=True,
            package=build_research_package(property_snapshot),
        )


class StubSynthesisService:
    async def run(self, *, request_id: str, payload: object) -> AgentResearchRunResponse:
        del request_id, payload
        return AgentResearchRunResponse(
            success=True,
            package=build_agent_research_package(),
            warnings=[],
        )


class StubCommitteeService:
    async def analyze_with_details(
        self,
        *,
        request_id: str,
        committee_input: object,
        analysis_id: str | None = None,
    ) -> InvestmentCommitteeAnalysisResult:
        del committee_input, analysis_id
        now = datetime.now(UTC)
        return InvestmentCommitteeAnalysisResult(
            output=build_committee_output(),
            execution_metadata=CommitteeExecutionMetadata(
                request_id=request_id,
                workflow_name="investment_committee",
                agent_version="investment_committee_agent:v1",
                prompt_version="v1",
                input_format_version="v1",
                recommendation_policy_version="v1",
                offer_range_policy_version="v1",
                confidence_policy_version="v1",
                model="gpt-5-mini",
                validation_status="passed",
                started_at=now,
                completed_at=now,
            ),
            usage_metadata=CommitteeUsageMetadata(),
            warnings=["committee-warning"],
        )


class FailingResearchOrchestrator:
    async def research(self, request: ResearchPackageRequest) -> ResearchPackageResponse:
        del request
        raise AppError(
            code="research_timeout",
            message="Research timed out.",
            status_code=504,
            retryable=True,
        )


@pytest.mark.asyncio
async def test_analysis_execution_service_persists_successful_outputs(db_session: Session) -> None:
    property_snapshot = build_verified_property()
    assumptions = build_assumptions()
    property_record = PropertyRepository(db_session).create(verified_property=property_snapshot)
    analysis = AnalysisRepository(db_session).create(
        property_id=property_record.id,
        property_snapshot=property_snapshot,
        assumptions_snapshot=assumptions,
    )
    session_factory = create_session_factory(cast(Engine, db_session.get_bind()))
    service = AnalysisExecutionService(
        session_factory=session_factory,
        underwriting_service=UnderwritingService(),
        research_orchestrator=StubResearchOrchestrator(),
        synthesis_service=StubSynthesisService(),
        committee_service=StubCommitteeService(),
    )

    await service.run_analysis(analysis_id=analysis.id, request_id="req-success")

    verification_session = session_factory()
    persisted = AnalysisRepository(verification_session).get_required_by_id(analysis.id)
    deserialized = deserialize_analysis_record(persisted)
    verification_session.close()

    assert persisted.status == AnalysisStatus.COMPLETED
    assert persisted.current_stage == AnalysisStage.PERSISTENCE
    assert persisted.completed_at is not None
    assert deserialized.underwriting_result is not None
    assert deserialized.research_result is not None
    assert deserialized.agent_research_result is not None
    assert deserialized.investment_committee_result is not None
    assert deserialized.execution_metadata is not None
    assert deserialized.execution_metadata["status"] == "completed"
    assert deserialized.execution_metadata["current_stage"] == "persistence"
    assert deserialized.execution_metadata["versions"]["calculation_version"] == "v1"
    assert deserialized.execution_metadata["versions"]["committee_prompt_version"] == "v1"


@pytest.mark.asyncio
async def test_analysis_execution_service_persists_failure_stage_and_metadata(
    db_session: Session,
) -> None:
    property_snapshot = build_verified_property()
    assumptions = build_assumptions()
    property_record = PropertyRepository(db_session).create(verified_property=property_snapshot)
    analysis = AnalysisRepository(db_session).create(
        property_id=property_record.id,
        property_snapshot=property_snapshot,
        assumptions_snapshot=assumptions,
    )
    session_factory = create_session_factory(cast(Engine, db_session.get_bind()))
    service = AnalysisExecutionService(
        session_factory=session_factory,
        underwriting_service=UnderwritingService(),
        research_orchestrator=FailingResearchOrchestrator(),
        synthesis_service=StubSynthesisService(),
        committee_service=StubCommitteeService(),
    )

    with pytest.raises(AppError) as exc_info:
        await service.run_analysis(analysis_id=analysis.id, request_id="req-failure")

    assert exc_info.value.code == "research_timeout"

    verification_session = session_factory()
    persisted = AnalysisRepository(verification_session).get_required_by_id(analysis.id)
    deserialized = deserialize_analysis_record(persisted)
    verification_session.close()

    assert persisted.status == AnalysisStatus.FAILED
    assert persisted.failure_stage == AnalysisStage.RESEARCH
    assert persisted.error_code == "research_timeout"
    assert persisted.error_message == "Research timed out."
    assert deserialized.underwriting_result is not None
    assert deserialized.research_result is None
    assert deserialized.execution_metadata is not None
    assert deserialized.execution_metadata["failure"]["stage"] == "research"
    assert deserialized.execution_metadata["failure"]["error_code"] == "research_timeout"


@pytest.mark.asyncio
async def test_background_execution_is_isolated_behind_task_runner(db_session: Session) -> None:
    property_snapshot = build_verified_property()
    assumptions = build_assumptions()
    property_record = PropertyRepository(db_session).create(verified_property=property_snapshot)
    analysis = AnalysisRepository(db_session).create(
        property_id=property_record.id,
        property_snapshot=property_snapshot,
        assumptions_snapshot=assumptions,
    )
    session_factory = create_session_factory(cast(Engine, db_session.get_bind()))
    service = AnalysisExecutionService(
        session_factory=session_factory,
        underwriting_service=UnderwritingService(),
        research_orchestrator=StubResearchOrchestrator(),
        synthesis_service=StubSynthesisService(),
        committee_service=StubCommitteeService(),
        task_runner=InProcessAnalysisTaskRunner(),
    )

    task = service.start_background_analysis(analysis_id=analysis.id, request_id="req-background")
    await task

    verification_session = session_factory()
    persisted = AnalysisRepository(verification_session).get_required_by_id(analysis.id)
    verification_session.close()

    assert persisted.status == AnalysisStatus.COMPLETED
