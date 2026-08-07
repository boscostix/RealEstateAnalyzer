"""Service tests for Milestone 6 Phase 2."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.analysis_persistence import deserialize_analysis_record
from app.db.repositories import AnalysisRepository, PropertyRepository
from app.services.property_service import PropertyService
from tests.db.factories import (
    build_assumptions,
    build_normalized_property,
    build_verified_property,
)


def test_property_service_creates_and_loads_snapshots(db_session: Session) -> None:
    service = PropertyService(PropertyRepository(db_session))

    created = service.create_property(
        normalized_property=build_normalized_property(),
        verified_property=build_verified_property(),
    )
    normalized, verified = service.get_property_snapshots(created.id)

    assert normalized is not None
    assert verified is not None
    assert normalized.address.city == "Dallas"
    assert verified.asking_price.final_value == Decimal("445000")


def test_property_service_updates_verified_snapshot(db_session: Session) -> None:
    service = PropertyService(PropertyRepository(db_session))
    created = service.create_property(
        normalized_property=build_normalized_property(),
        verified_property=build_verified_property(),
    )

    service.update_property(
        created.id,
        verified_property=build_verified_property("430000"),
        current_version=2,
    )
    _, verified = service.get_property_snapshots(created.id)

    assert verified is not None
    assert verified.asking_price.final_value == Decimal("430000")


def test_property_update_does_not_mutate_historical_analysis_snapshot(db_session: Session) -> None:
    property_service = PropertyService(PropertyRepository(db_session))
    analysis_repository = AnalysisRepository(db_session)
    created = property_service.create_property(
        normalized_property=build_normalized_property(),
        verified_property=build_verified_property("445000"),
    )
    _, original_verified = property_service.get_property_snapshots(created.id)
    assert original_verified is not None

    analysis = analysis_repository.create(
        property_id=created.id,
        property_snapshot=original_verified,
        assumptions_snapshot=build_assumptions(),
    )

    property_service.update_property(
        created.id,
        normalized_property=build_normalized_property("430000"),
        verified_property=build_verified_property("430000"),
        current_version=2,
    )
    persisted_analysis = deserialize_analysis_record(
        analysis_repository.get_required_by_id(analysis.id)
    )
    _, current_verified = property_service.get_property_snapshots(created.id)

    assert current_verified is not None
    assert persisted_analysis.property_snapshot is not None
    assert current_verified.asking_price.final_value == Decimal("430000")
    assert persisted_analysis.property_snapshot.asking_price.final_value == Decimal("445000")
