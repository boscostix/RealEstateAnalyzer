"""ORM model tests for Milestone 6 Phase 1."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import AnalysisRecord, AnalysisStage, AnalysisStatus, PropertyRecord


def test_create_property_and_analysis_relationship(db_session: Session) -> None:
    property_row = PropertyRecord(
        source_url="https://example.com/listing/123",
        provider="zillow",
        listing_id="123",
        full_address="123 Main St, Dallas, TX 75001",
        city="Dallas",
        state="TX",
        postal_code="75001",
        latitude=Decimal("32.7767000"),
        longitude=Decimal("-96.7970000"),
        normalized_property_json={"schema_version": "v1", "data": {"asking_price": "450000"}},
        verified_property_json={"schema_version": "v1", "data": {"asking_price": "445000"}},
    )
    analysis_row = AnalysisRecord(
        version=1,
        status=AnalysisStatus.PENDING,
        current_stage=AnalysisStage.PREPARATION,
        property_snapshot_json={"schema_version": "v1", "data": {"asking_price": "445000"}},
        assumptions_snapshot_json={"schema_version": "v1", "data": {"purchase_price": "440000"}},
    )
    property_row.analyses.append(analysis_row)

    db_session.add(property_row)
    db_session.commit()
    db_session.refresh(property_row)

    loaded = db_session.get(PropertyRecord, property_row.id)
    assert loaded is not None
    assert loaded.analyses[0].property_id == property_row.id
    assert loaded.analyses[0].version == 1


def test_analysis_version_is_unique_per_property(db_session: Session) -> None:
    property_row = PropertyRecord(
        source_url="https://example.com/listing/456",
        provider="redfin",
    )
    db_session.add(property_row)
    db_session.commit()

    db_session.add_all(
        [
            AnalysisRecord(property_id=property_row.id, version=1, status=AnalysisStatus.PENDING),
            AnalysisRecord(property_id=property_row.id, version=1, status=AnalysisStatus.RUNNING),
        ]
    )

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_analysis_parent_linkage_persists(db_session: Session) -> None:
    property_row = PropertyRecord(
        source_url="https://example.com/listing/789",
        provider="zillow",
    )
    parent = AnalysisRecord(property=property_row, version=1, status=AnalysisStatus.COMPLETED)
    child = AnalysisRecord(
        property=property_row,
        version=2,
        status=AnalysisStatus.PENDING,
        parent_analysis=parent,
    )

    db_session.add_all([property_row, parent, child])
    db_session.commit()
    db_session.refresh(child)

    assert child.parent_analysis_id == parent.id
    assert parent.reruns[0].id == child.id


def test_timestamps_are_timezone_aware(db_session: Session) -> None:
    before_insert = datetime.now(UTC)
    property_row = PropertyRecord(
        source_url="https://example.com/listing/999",
        provider="zillow",
    )
    db_session.add(property_row)
    db_session.commit()
    db_session.refresh(property_row)

    assert property_row.created_at.tzinfo == UTC
    assert property_row.updated_at.tzinfo == UTC
    assert property_row.created_at >= before_insert
