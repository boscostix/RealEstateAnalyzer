"""API tests for the persisted analysis endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.api.persisted_analysis_routes import (
    get_analysis_execution_service,
    get_analysis_repository,
    get_property_service,
)
from app.db.base import Base
from app.db.models import AnalysisStage, AnalysisStatus
from app.db.repositories import AnalysisRepository, PropertyRepository
from app.db.session import create_engine_from_url, create_session_factory
from app.main import app
from app.services.property_service import PropertyService
from tests.db.factories import (
    build_agent_research_package,
    build_assumptions,
    build_committee_output,
    build_normalized_property,
    build_research_package,
    build_underwriting_result,
    build_verified_property,
)

DB_PATH = Path("/private/tmp/real_estate_phase5_api_test.db")
ENGINE = create_engine_from_url(f"sqlite+pysqlite:///{DB_PATH}")
SESSION_FACTORY = create_session_factory(ENGINE)
client = TestClient(app, raise_server_exceptions=False)


class NoOpExecutionService:
    def start_background_analysis(self, *, analysis_id: str, request_id: str) -> None:
        del analysis_id, request_id


def override_property_service() -> PropertyService:
    return PropertyService(PropertyRepository(SESSION_FACTORY()))


def override_analysis_repository() -> AnalysisRepository:
    return AnalysisRepository(SESSION_FACTORY())


def setup_module(module: object) -> None:
    Base.metadata.drop_all(ENGINE)
    Base.metadata.create_all(ENGINE)
    app.dependency_overrides[get_property_service] = override_property_service
    app.dependency_overrides[get_analysis_repository] = override_analysis_repository
    app.dependency_overrides[get_analysis_execution_service] = lambda: NoOpExecutionService()


def teardown_module(module: object) -> None:
    app.dependency_overrides.clear()
    Base.metadata.drop_all(ENGINE)
    ENGINE.dispose()
    if DB_PATH.exists():
        DB_PATH.unlink()


def _reset_db() -> None:
    Base.metadata.drop_all(ENGINE)
    Base.metadata.create_all(ENGINE)


def test_create_analysis_endpoint_creates_pending_analysis_and_stable_id() -> None:
    _reset_db()
    session = SESSION_FACTORY()
    property_record = PropertyRepository(session).create(
        normalized_property=build_normalized_property(),
        verified_property=build_verified_property(),
    )
    session.close()

    response = client.post(
        f"/api/v1/properties/{property_record.id}/analyses",
        json={"assumptions": build_assumptions().model_dump(mode="json")},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["success"] is True
    assert isinstance(body["analysis"]["id"], str)
    assert body["analysis"]["property_id"] == property_record.id
    assert body["analysis"]["status"] == "pending"
    assert body["analysis"]["version"] == 1


def test_get_analysis_endpoint_returns_running_state_with_execution_metadata() -> None:
    _reset_db()
    session = SESSION_FACTORY()
    property_record = PropertyRepository(session).create(
        verified_property=build_verified_property()
    )
    analysis_repository = AnalysisRepository(session)
    analysis = analysis_repository.create(
        property_id=property_record.id,
        property_snapshot=build_verified_property(),
        assumptions_snapshot=build_assumptions(),
    )
    analysis_repository.update_results(
        analysis.id,
        execution_metadata={"status": "running", "current_stage": "research", "stage_history": []},
        current_stage=AnalysisStage.RESEARCH,
    )
    analysis_repository.update_status(
        analysis.id,
        status=AnalysisStatus.RUNNING,
        current_stage=AnalysisStage.RESEARCH,
    )
    session.close()

    response = client.get(f"/api/v1/analyses/{analysis.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["analysis"]["status"] == "running"
    assert body["analysis"]["current_stage"] == "research"
    assert body["analysis"]["execution"]["status"] == "running"
    assert body["analysis"]["underwriting"] is None


def test_get_analysis_endpoint_returns_completed_full_report() -> None:
    _reset_db()
    property_snapshot = build_verified_property()
    assumptions = build_assumptions()
    session = SESSION_FACTORY()
    property_record = PropertyRepository(session).create(verified_property=property_snapshot)
    analysis_repository = AnalysisRepository(session)
    analysis = analysis_repository.create(
        property_id=property_record.id,
        property_snapshot=property_snapshot,
        assumptions_snapshot=assumptions,
    )
    analysis_repository.update_results(
        analysis.id,
        underwriting_result=build_underwriting_result(property_snapshot, assumptions),
        research_result=build_research_package(property_snapshot),
        agent_research_result=build_agent_research_package(),
        investment_committee_result=build_committee_output(),
        execution_metadata={"status": "completed", "current_stage": "persistence"},
        current_stage=AnalysisStage.PERSISTENCE,
    )
    analysis_repository.update_status(
        analysis.id,
        status=AnalysisStatus.RUNNING,
        current_stage=AnalysisStage.INVESTMENT_COMMITTEE,
    )
    analysis_repository.update_status(
        analysis.id,
        status=AnalysisStatus.COMPLETED,
        current_stage=AnalysisStage.PERSISTENCE,
    )
    session.close()

    response = client.get(f"/api/v1/analyses/{analysis.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["analysis"]["status"] == "completed"
    assert body["analysis"]["underwriting"]["metrics"]["noi"] is not None
    assert body["analysis"]["research"]["metadata"]["completed_domains"] == ["public_records"]
    assert body["analysis"]["agent_research"]["overall_data_confidence"] == "0.75"
    assert body["analysis"]["investment_committee"]["recommendation"] == "negotiate"


def test_get_analysis_endpoint_returns_safe_failure_information() -> None:
    _reset_db()
    session = SESSION_FACTORY()
    property_record = PropertyRepository(session).create(
        verified_property=build_verified_property()
    )
    analysis_repository = AnalysisRepository(session)
    analysis = analysis_repository.create(
        property_id=property_record.id,
        property_snapshot=build_verified_property(),
        assumptions_snapshot=build_assumptions(),
    )
    analysis_repository.update_results(
        analysis.id,
        execution_metadata={
            "status": "failed",
            "current_stage": "research",
            "failure": {"stage": "research", "error_code": "research_timeout"},
        },
        current_stage=AnalysisStage.RESEARCH,
    )
    analysis_repository.update_status(
        analysis.id,
        status=AnalysisStatus.RUNNING,
        current_stage=AnalysisStage.RESEARCH,
    )
    analysis_repository.update_status(
        analysis.id,
        status=AnalysisStatus.FAILED,
        current_stage=AnalysisStage.RESEARCH,
        failure_stage=AnalysisStage.RESEARCH,
        error_code="research_timeout",
        error_message="Research timed out.",
    )
    session.close()

    response = client.get(f"/api/v1/analyses/{analysis.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["analysis"]["status"] == "failed"
    assert body["analysis"]["failure_stage"] == "research"
    assert body["analysis"]["error_code"] == "research_timeout"
    assert body["analysis"]["error_message"] == "Research timed out."
    assert body["analysis"]["execution"]["failure"]["error_code"] == "research_timeout"


def test_list_property_analyses_returns_lightweight_history() -> None:
    _reset_db()
    session = SESSION_FACTORY()
    property_record = PropertyRepository(session).create(
        verified_property=build_verified_property()
    )
    analysis_repository = AnalysisRepository(session)
    first = analysis_repository.create(
        property_id=property_record.id,
        property_snapshot=build_verified_property("445000"),
        assumptions_snapshot=build_assumptions(),
    )
    second = analysis_repository.create(
        property_id=property_record.id,
        property_snapshot=build_verified_property("430000"),
        assumptions_snapshot=build_assumptions("425000"),
    )
    session.close()

    response = client.get(f"/api/v1/properties/{property_record.id}/analyses")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert [analysis["version"] for analysis in body["analyses"]] == [2, 1]
    assert body["analyses"][0]["id"] == second.id
    assert body["analyses"][1]["id"] == first.id
