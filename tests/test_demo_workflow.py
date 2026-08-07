"""End-to-end persisted demo workflow tests for Milestone 6 hardening."""

from __future__ import annotations

from collections.abc import Callable, Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.api.persisted_analysis_routes import (
    get_analysis_execution_service,
    get_analysis_repository,
    get_property_service,
)
from app.api.property_routes import get_analysis_repository as get_property_analysis_repository
from app.api.property_routes import get_property_service as get_property_route_service
from app.db.analysis_persistence import deserialize_analysis_record
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


class ImmediateExecutionService:
    """Test execution service that completes analyses synchronously."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def start_background_analysis(self, *, analysis_id: str, request_id: str) -> None:
        del request_id
        session = self._session_factory()
        try:
            repository = AnalysisRepository(session)
            analysis = repository.get_required_by_id(analysis_id)
            persisted = deserialize_analysis_record(analysis)
            assert persisted.property_snapshot is not None
            assert persisted.assumptions_snapshot is not None

            repository.update_status(
                analysis_id,
                status=AnalysisStatus.RUNNING,
                current_stage=AnalysisStage.UNDERWRITING,
            )
            repository.update_results(
                analysis_id,
                underwriting_result=build_underwriting_result(
                    persisted.property_snapshot,
                    persisted.assumptions_snapshot,
                ),
                research_result=build_research_package(persisted.property_snapshot),
                agent_research_result=build_agent_research_package(),
                investment_committee_result=build_committee_output(),
                execution_metadata={
                    "status": "completed",
                    "current_stage": "persistence",
                    "stage_history": [
                        {"stage": "preparation"},
                        {"stage": "underwriting"},
                        {"stage": "research"},
                        {"stage": "agent_research"},
                        {"stage": "investment_committee"},
                        {"stage": "persistence"},
                    ],
                    "warnings": [],
                },
                current_stage=AnalysisStage.PERSISTENCE,
            )
            repository.update_status(
                analysis_id,
                status=AnalysisStatus.COMPLETED,
                current_stage=AnalysisStage.PERSISTENCE,
            )
        finally:
            session.close()


class FailingExecutionService:
    """Test execution service that records a persisted failure."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def start_background_analysis(self, *, analysis_id: str, request_id: str) -> None:
        del request_id
        session = self._session_factory()
        try:
            repository = AnalysisRepository(session)
            repository.update_status(
                analysis_id,
                status=AnalysisStatus.RUNNING,
                current_stage=AnalysisStage.RESEARCH,
            )
            repository.update_results(
                analysis_id,
                execution_metadata={
                    "status": "failed",
                    "current_stage": "research",
                    "failure": {
                        "stage": "research",
                        "error_code": "research_timeout",
                        "error_message": "Research timed out.",
                    },
                },
                current_stage=AnalysisStage.RESEARCH,
            )
            repository.update_status(
                analysis_id,
                status=AnalysisStatus.FAILED,
                current_stage=AnalysisStage.RESEARCH,
                failure_stage=AnalysisStage.RESEARCH,
                error_code="research_timeout",
                error_message="Research timed out.",
            )
        finally:
            session.close()


def _override_property_service(session_factory: Callable[[], Session]) -> PropertyService:
    return PropertyService(PropertyRepository(session_factory()))


def _override_analysis_repository(session_factory: Callable[[], Session]) -> AnalysisRepository:
    return AnalysisRepository(session_factory())


def _install_overrides(session_factory: Callable[[], Session], execution_service: object) -> None:
    app.dependency_overrides[get_property_service] = lambda: _override_property_service(
        session_factory
    )
    app.dependency_overrides[get_property_route_service] = lambda: _override_property_service(
        session_factory
    )
    app.dependency_overrides[get_analysis_repository] = lambda: _override_analysis_repository(
        session_factory
    )
    app.dependency_overrides[get_property_analysis_repository] = lambda: (
        _override_analysis_repository(session_factory)
    )
    app.dependency_overrides[get_analysis_execution_service] = lambda: execution_service


@pytest.fixture
def persisted_api_client(
    tmp_path: Path,
) -> Generator[tuple[TestClient, Callable[[], Session], Path], None, None]:
    database_path = tmp_path / "phase7_demo_workflow.db"
    engine = create_engine_from_url(f"sqlite+pysqlite:///{database_path}")
    session_factory = create_session_factory(engine)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    _install_overrides(session_factory, ImmediateExecutionService(session_factory))
    client = TestClient(app, raise_server_exceptions=False)
    try:
        yield client, session_factory, database_path
    finally:
        client.close()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_demo_workflow_supports_create_update_run_history_and_rerun(
    persisted_api_client: tuple[TestClient, Callable[[], Session], Path],
) -> None:
    client, session_factory, _database_path = persisted_api_client

    create_response = client.post(
        "/api/v1/properties",
        json={
            "property": build_normalized_property("445000").model_dump(mode="json"),
            "verified_property": build_verified_property("445000").model_dump(mode="json"),
        },
    )
    assert create_response.status_code == 201
    property_id = create_response.json()["property"]["id"]

    patch_response = client.patch(
        f"/api/v1/properties/{property_id}",
        json={
            "property": build_normalized_property("430000").model_dump(mode="json"),
            "verified_property": build_verified_property("430000").model_dump(mode="json"),
            "current_version": 2,
        },
    )
    assert patch_response.status_code == 200
    patched_property = patch_response.json()["property"]
    assert patched_property["verified_property"]["asking_price"]["final_value"] == "430000"

    create_analysis_response = client.post(
        f"/api/v1/properties/{property_id}/analyses",
        json={"assumptions": build_assumptions().model_dump(mode="json")},
    )
    assert create_analysis_response.status_code == 202
    analysis_id = create_analysis_response.json()["analysis"]["id"]

    analysis_response = client.get(f"/api/v1/analyses/{analysis_id}")
    assert analysis_response.status_code == 200
    analysis_body = analysis_response.json()["analysis"]
    assert analysis_body["status"] == "completed"
    assert analysis_body["underwriting"]["metrics"]["noi"] is not None
    assert analysis_body["property_snapshot"]["asking_price"]["final_value"] == "430000"

    history_response = client.get(f"/api/v1/properties/{property_id}/analyses")
    assert history_response.status_code == 200
    assert [item["version"] for item in history_response.json()["analyses"]] == [1]

    rerun_response = client.post(
        f"/api/v1/analyses/{analysis_id}/rerun",
        json={"assumption_overrides": {"financing": {"interest_rate_percent": "7.10"}}},
    )
    assert rerun_response.status_code == 202
    rerun_id = rerun_response.json()["analysis"]["id"]
    assert rerun_response.json()["analysis"]["parent_analysis_id"] == analysis_id

    rerun_detail_response = client.get(f"/api/v1/analyses/{rerun_id}")
    assert rerun_detail_response.status_code == 200
    assert rerun_detail_response.json()["analysis"]["status"] == "completed"

    final_history_response = client.get(f"/api/v1/properties/{property_id}/analyses")
    assert final_history_response.status_code == 200
    final_history = final_history_response.json()["analyses"]
    assert [item["version"] for item in final_history] == [2, 1]
    assert final_history[0]["parent_analysis_id"] == analysis_id

    verification_session: Session = session_factory()
    try:
        first_analysis = AnalysisRepository(verification_session).get_required_by_id(analysis_id)
        rerun_analysis = AnalysisRepository(verification_session).get_required_by_id(rerun_id)
        first_snapshot = deserialize_analysis_record(first_analysis)
        rerun_snapshot = deserialize_analysis_record(rerun_analysis)
        assert first_snapshot.property_snapshot is not None
        assert rerun_snapshot.property_snapshot is not None
        assert str(first_snapshot.property_snapshot.asking_price.final_value) == "430000"
        assert str(rerun_snapshot.property_snapshot.asking_price.final_value) == "430000"
        assert rerun_snapshot.assumptions_snapshot is not None
        assert str(rerun_snapshot.assumptions_snapshot.financing.interest_rate_percent) == "7.10"
    finally:
        verification_session.close()


def test_completed_analysis_history_survives_fastapi_restart(
    persisted_api_client: tuple[TestClient, Callable[[], Session], Path],
) -> None:
    client, session_factory, database_path = persisted_api_client

    create_response = client.post(
        "/api/v1/properties",
        json={
            "property": build_normalized_property().model_dump(mode="json"),
            "verified_property": build_verified_property().model_dump(mode="json"),
        },
    )
    property_id = create_response.json()["property"]["id"]
    analysis_response = client.post(
        f"/api/v1/properties/{property_id}/analyses",
        json={"assumptions": build_assumptions().model_dump(mode="json")},
    )
    analysis_id = analysis_response.json()["analysis"]["id"]
    client.close()

    app.dependency_overrides.clear()
    restarted_engine = create_engine_from_url(f"sqlite+pysqlite:///{database_path}")
    restarted_session_factory = create_session_factory(restarted_engine)
    _install_overrides(
        restarted_session_factory,
        ImmediateExecutionService(restarted_session_factory),
    )
    restarted_client = TestClient(app, raise_server_exceptions=False)
    try:
        get_analysis_response = restarted_client.get(f"/api/v1/analyses/{analysis_id}")
        assert get_analysis_response.status_code == 200
        assert get_analysis_response.json()["analysis"]["status"] == "completed"

        history_response = restarted_client.get(f"/api/v1/properties/{property_id}/analyses")
        assert history_response.status_code == 200
        assert len(history_response.json()["analyses"]) == 1
    finally:
        restarted_client.close()
        app.dependency_overrides.clear()
        restarted_engine.dispose()


def test_failed_analysis_detail_and_history_are_persisted(tmp_path: Path) -> None:
    database_path = tmp_path / "phase7_failure_workflow.db"
    engine = create_engine_from_url(f"sqlite+pysqlite:///{database_path}")
    session_factory = create_session_factory(engine)
    Base.metadata.create_all(engine)
    _install_overrides(session_factory, FailingExecutionService(session_factory))
    client = TestClient(app, raise_server_exceptions=False)
    try:
        create_response = client.post(
            "/api/v1/properties",
            json={
                "property": build_normalized_property().model_dump(mode="json"),
                "verified_property": build_verified_property().model_dump(mode="json"),
            },
        )
        property_id = create_response.json()["property"]["id"]

        analysis_response = client.post(
            f"/api/v1/properties/{property_id}/analyses",
            json={"assumptions": build_assumptions().model_dump(mode="json")},
        )
        assert analysis_response.status_code == 202
        analysis_id = analysis_response.json()["analysis"]["id"]

        detail_response = client.get(f"/api/v1/analyses/{analysis_id}")
        assert detail_response.status_code == 200
        detail = detail_response.json()["analysis"]
        assert detail["status"] == "failed"
        assert detail["failure_stage"] == "research"
        assert detail["execution"]["failure"]["error_code"] == "research_timeout"

        history_response = client.get(f"/api/v1/properties/{property_id}/analyses")
        assert history_response.status_code == 200
        assert history_response.json()["analyses"][0]["status"] == "failed"
    finally:
        client.close()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_database_indexes_support_property_lookup_and_analysis_history(tmp_path: Path) -> None:
    database_path = tmp_path / "phase7_indexes.db"
    engine = create_engine_from_url(f"sqlite+pysqlite:///{database_path}")
    Base.metadata.create_all(engine)
    try:
        inspector = inspect(engine)
        property_indexes = {index["name"] for index in inspector.get_indexes("properties")}
        analysis_indexes = {index["name"] for index in inspector.get_indexes("analyses")}

        assert "ix_properties_provider" in property_indexes
        assert "ix_properties_full_address" in property_indexes
        assert "ix_properties_created_at" in property_indexes
        assert "ix_analyses_property_created" in analysis_indexes
        assert "ix_analyses_status" in analysis_indexes
        assert "ix_analyses_property_id" in analysis_indexes
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()
