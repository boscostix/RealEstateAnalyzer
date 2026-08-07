"""Repository tests for Milestone 6 Phase 2."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.db.analysis_persistence import (
    deserialize_analysis_record,
    stage_allows_status,
)
from app.db.models import AnalysisStage, AnalysisStatus
from app.db.repositories import AnalysisRepository, PropertyRepository
from app.exceptions import AnalysisImmutableError, InvalidAnalysisStateError, PropertyNotFoundError
from tests.db.factories import (
    build_agent_research_package,
    build_assumptions,
    build_committee_output,
    build_normalized_property,
    build_research_package,
    build_underwriting_result,
    build_verified_property,
)


def test_property_repository_create_and_retrieve(db_session: Session) -> None:
    repository = PropertyRepository(db_session)

    created = repository.create(
        normalized_property=build_normalized_property(),
        verified_property=build_verified_property(),
    )
    loaded = repository.get_required_by_id(created.id)

    assert loaded.id == created.id
    assert loaded.full_address == "123 Main St, Dallas, TX 75001"
    assert loaded.property_schema_version == "v1"
    assert loaded.verified_property_schema_version == "v1"


def test_property_repository_update_and_not_found(db_session: Session) -> None:
    repository = PropertyRepository(db_session)
    created = repository.create(verified_property=build_verified_property())

    updated = repository.update(
        created.id,
        verified_property=build_verified_property("430000"),
        current_version=2,
    )

    assert updated.current_version == 2
    assert updated.full_address == "123 Main St, Dallas, TX 75001"
    assert updated.verified_property_json is not None
    assert updated.verified_property_json["data"]["asking_price"]["final_value"] == "430000"

    with pytest.raises(PropertyNotFoundError):
        repository.get_required_by_id("missing-property")


def test_analysis_repository_create_retrieve_history_and_latest(db_session: Session) -> None:
    property_repository = PropertyRepository(db_session)
    analysis_repository = AnalysisRepository(db_session)
    property_record = property_repository.create(verified_property=build_verified_property())

    first = analysis_repository.create(
        property_id=property_record.id,
        property_snapshot=build_verified_property("445000"),
        assumptions_snapshot=build_assumptions("440000"),
    )
    second = analysis_repository.create(
        property_id=property_record.id,
        property_snapshot=build_verified_property("430000"),
        assumptions_snapshot=build_assumptions("425000"),
    )

    loaded = analysis_repository.get_required_by_id(first.id)
    history = analysis_repository.list_for_property(property_record.id)
    latest = analysis_repository.get_latest_for_property(property_record.id)

    assert loaded.version == 1
    assert second.version == 2
    assert [analysis.version for analysis in history] == [2, 1]
    assert latest is not None
    assert latest.id == second.id


def test_analysis_repository_parent_linkage_and_version_increment(db_session: Session) -> None:
    property_record = PropertyRepository(db_session).create(
        verified_property=build_verified_property()
    )
    repository = AnalysisRepository(db_session)

    original = repository.create(
        property_id=property_record.id,
        property_snapshot=build_verified_property(),
        assumptions_snapshot=build_assumptions(),
    )
    rerun = repository.create(
        property_id=property_record.id,
        property_snapshot=build_verified_property("430000"),
        assumptions_snapshot=build_assumptions("425000"),
        parent_analysis_id=original.id,
    )

    assert rerun.version == 2
    assert rerun.parent_analysis_id == original.id


def test_analysis_repository_status_transitions_are_validated(db_session: Session) -> None:
    property_record = PropertyRepository(db_session).create(
        verified_property=build_verified_property()
    )
    repository = AnalysisRepository(db_session)
    analysis = repository.create(
        property_id=property_record.id,
        property_snapshot=build_verified_property(),
        assumptions_snapshot=build_assumptions(),
    )

    running = repository.update_status(
        analysis.id,
        status=AnalysisStatus.RUNNING,
        current_stage=AnalysisStage.UNDERWRITING,
    )
    assert running.started_at is not None
    assert running.current_stage == AnalysisStage.UNDERWRITING
    assert stage_allows_status(running.current_stage, running.status) is True

    completed = repository.update_status(
        analysis.id,
        status=AnalysisStatus.COMPLETED,
        current_stage=AnalysisStage.PERSISTENCE,
    )
    assert completed.completed_at is not None

    with pytest.raises(InvalidAnalysisStateError):
        repository.update_status(
            analysis.id,
            status=AnalysisStatus.RUNNING,
            current_stage=AnalysisStage.RESEARCH,
        )


def test_analysis_repository_persists_and_deserializes_results(db_session: Session) -> None:
    property_snapshot = build_verified_property()
    assumptions = build_assumptions()
    property_record = PropertyRepository(db_session).create(verified_property=property_snapshot)
    repository = AnalysisRepository(db_session)
    analysis = repository.create(
        property_id=property_record.id,
        property_snapshot=property_snapshot,
        assumptions_snapshot=assumptions,
    )

    updated = repository.update_results(
        analysis.id,
        underwriting_result=build_underwriting_result(property_snapshot, assumptions),
        research_result=build_research_package(property_snapshot),
        agent_research_result=build_agent_research_package(),
        investment_committee_result=build_committee_output(),
        execution_metadata={"duration_ms": 42},
        current_stage=AnalysisStage.INVESTMENT_COMMITTEE,
    )
    deserialized = deserialize_analysis_record(updated)

    assert deserialized.property_snapshot is not None
    assert deserialized.property_snapshot.asking_price.final_value == Decimal("445000")
    assert deserialized.underwriting_result is not None
    assert deserialized.research_result is not None
    assert deserialized.agent_research_result is not None
    assert deserialized.investment_committee_result is not None
    assert deserialized.execution_metadata == {"duration_ms": 42}
    assert deserialized.underwriting_schema_version == "v1"


def test_completed_analysis_cannot_be_mutated(db_session: Session) -> None:
    property_snapshot = build_verified_property()
    assumptions = build_assumptions()
    property_record = PropertyRepository(db_session).create(verified_property=property_snapshot)
    repository = AnalysisRepository(db_session)
    analysis = repository.create(
        property_id=property_record.id,
        property_snapshot=property_snapshot,
        assumptions_snapshot=assumptions,
    )

    repository.update_status(
        analysis.id,
        status=AnalysisStatus.RUNNING,
        current_stage=AnalysisStage.UNDERWRITING,
    )
    repository.update_status(
        analysis.id,
        status=AnalysisStatus.COMPLETED,
        current_stage=AnalysisStage.PERSISTENCE,
    )

    with pytest.raises(AnalysisImmutableError):
        repository.update_results(
            analysis.id,
            execution_metadata={"duration_ms": 99},
        )
