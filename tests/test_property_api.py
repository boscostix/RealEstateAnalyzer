"""API tests for the Phase 3 property persistence endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.api.property_routes import get_analysis_repository, get_property_service
from app.db.analysis_persistence import deserialize_analysis_record
from app.db.base import Base
from app.db.models import AnalysisStage, AnalysisStatus
from app.db.repositories import AnalysisRepository, PropertyRepository
from app.db.session import create_engine_from_url, create_session_factory
from app.main import app
from app.services.property_service import PropertyService
from tests.db.factories import build_assumptions, build_normalized_property, build_verified_property

DB_PATH = Path("/private/tmp/real_estate_phase3_api_test.db")
ENGINE = create_engine_from_url(f"sqlite+pysqlite:///{DB_PATH}")
SESSION_FACTORY = create_session_factory(ENGINE)
client = TestClient(app, raise_server_exceptions=False)


def override_property_service() -> PropertyService:
    return PropertyService(PropertyRepository(SESSION_FACTORY()))


def override_analysis_repository() -> AnalysisRepository:
    return AnalysisRepository(SESSION_FACTORY())


def setup_module(module: object) -> None:
    Base.metadata.drop_all(ENGINE)
    Base.metadata.create_all(ENGINE)
    app.dependency_overrides[get_property_service] = override_property_service
    app.dependency_overrides[get_analysis_repository] = override_analysis_repository


def teardown_module(module: object) -> None:
    app.dependency_overrides.clear()
    Base.metadata.drop_all(ENGINE)
    ENGINE.dispose()
    if DB_PATH.exists():
        DB_PATH.unlink()


def _reset_db() -> None:
    Base.metadata.drop_all(ENGINE)
    Base.metadata.create_all(ENGINE)


def test_create_property_endpoint_returns_stable_id() -> None:
    _reset_db()
    response = client.post(
        "/api/v1/properties",
        json={
            "property": build_normalized_property().model_dump(mode="json"),
            "verified_property": build_verified_property().model_dump(mode="json"),
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert isinstance(body["property"]["id"], str)
    assert body["property"]["provider"] == "zillow"
    assert body["property"]["full_address"] == "123 Main St, Dallas, TX 75001"


def test_get_property_endpoint_returns_summary_verified_state_and_latest_analysis() -> None:
    _reset_db()
    session = SESSION_FACTORY()
    property_record = PropertyRepository(session).create(
        normalized_property=build_normalized_property(),
        verified_property=build_verified_property(),
    )
    analysis_repository = AnalysisRepository(session)
    analysis = analysis_repository.create(
        property_id=property_record.id,
        property_snapshot=build_verified_property(),
        assumptions_snapshot=build_assumptions(),
    )
    analysis_repository.update_status(
        analysis.id,
        status=AnalysisStatus.RUNNING,
        current_stage=AnalysisStage.UNDERWRITING,
    )
    session.close()

    response = client.get(f"/api/v1/properties/{property_record.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["property"]["id"] == property_record.id
    assert body["property"]["analysis_count"] == 1
    assert body["property"]["verified_property"]["asking_price"]["final_value"] == "445000"
    assert body["property"]["latest_analysis"]["version"] == 1
    assert body["property"]["latest_analysis"]["status"] == "running"
    assert "property_snapshot" not in body["property"]


def test_get_property_endpoint_returns_structured_not_found_error() -> None:
    _reset_db()

    response = client.get("/api/v1/properties/missing-property")

    assert response.status_code == 404
    assert response.json() == {
        "success": False,
        "error": {
            "code": "property_not_found",
            "message": "The requested property does not exist.",
            "retryable": False,
        },
    }


def test_patch_property_updates_verified_values() -> None:
    _reset_db()
    session = SESSION_FACTORY()
    property_record = PropertyRepository(session).create(
        normalized_property=build_normalized_property(),
        verified_property=build_verified_property(),
    )
    session.close()

    response = client.patch(
        f"/api/v1/properties/{property_record.id}",
        json={
            "verified_property": build_verified_property("430000").model_dump(mode="json"),
            "current_version": 2,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["property"]["current_version"] == 2
    assert body["property"]["verified_property"]["asking_price"]["final_value"] == "430000"


def test_patch_property_does_not_mutate_historical_analysis_snapshot() -> None:
    _reset_db()
    session = SESSION_FACTORY()
    property_record = PropertyRepository(session).create(
        normalized_property=build_normalized_property(),
        verified_property=build_verified_property("445000"),
    )
    analysis_repository = AnalysisRepository(session)
    analysis = analysis_repository.create(
        property_id=property_record.id,
        property_snapshot=build_verified_property("445000"),
        assumptions_snapshot=build_assumptions(),
    )
    session.close()

    response = client.patch(
        f"/api/v1/properties/{property_record.id}",
        json={
            "property": build_normalized_property("430000").model_dump(mode="json"),
            "verified_property": build_verified_property("430000").model_dump(mode="json"),
            "current_version": 2,
        },
    )

    assert response.status_code == 200

    verification_session = SESSION_FACTORY()
    persisted_analysis = deserialize_analysis_record(
        AnalysisRepository(verification_session).get_required_by_id(analysis.id)
    )
    verification_session.close()

    assert persisted_analysis.property_snapshot is not None
    assert str(persisted_analysis.property_snapshot.asking_price.final_value) == "445000"
