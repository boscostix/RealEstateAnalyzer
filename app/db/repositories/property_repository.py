"""Focused repository for persisted property records."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.models import PropertyRecord
from app.db.snapshots import (
    SNAPSHOT_SCHEMA_VERSION_V1,
    serialize_model_snapshot,
)
from app.exceptions import DatabaseOperationError, PropertyNotFoundError
from app.models.property import NormalizedProperty
from app.models.verification import VerifiedPropertySnapshot


class PropertyRepository:
    """Persistence operations for current property state."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        *,
        normalized_property: NormalizedProperty | None = None,
        verified_property: VerifiedPropertySnapshot | None = None,
    ) -> PropertyRecord:
        if normalized_property is None and verified_property is None:
            raise DatabaseOperationError(message="A property snapshot is required to create a row.")

        property_record = PropertyRecord()
        if normalized_property is not None:
            self._apply_normalized_snapshot(property_record, normalized_property)
        if verified_property is not None:
            self._apply_verified_snapshot(property_record, verified_property)
        property_record.created_at = datetime.now(UTC)
        property_record.updated_at = property_record.created_at

        self.session.add(property_record)
        self._commit_refresh(property_record)
        return property_record

    def get_by_id(self, property_id: str) -> PropertyRecord | None:
        return self.session.get(PropertyRecord, property_id)

    def get_required_by_id(self, property_id: str) -> PropertyRecord:
        property_record = self.get_by_id(property_id)
        if property_record is None:
            raise PropertyNotFoundError()
        return property_record

    def update(
        self,
        property_id: str,
        *,
        normalized_property: NormalizedProperty | None = None,
        verified_property: VerifiedPropertySnapshot | None = None,
        current_version: int | None = None,
    ) -> PropertyRecord:
        property_record = self.get_required_by_id(property_id)
        if normalized_property is not None:
            self._apply_normalized_snapshot(property_record, normalized_property)
        if verified_property is not None:
            self._apply_verified_snapshot(property_record, verified_property)
        if current_version is not None:
            property_record.current_version = current_version
        property_record.updated_at = datetime.now(UTC)
        self._commit_refresh(property_record)
        return property_record

    def _apply_normalized_snapshot(
        self,
        property_record: PropertyRecord,
        normalized_property: NormalizedProperty,
    ) -> None:
        property_record.source_url = normalized_property.source_url
        property_record.provider = normalized_property.provider
        property_record.listing_id = normalized_property.listing_id
        property_record.full_address = normalized_property.address.full_address
        property_record.street = normalized_property.address.street
        property_record.city = normalized_property.address.city
        property_record.state = normalized_property.address.state
        property_record.postal_code = normalized_property.address.postal_code
        property_record.latitude = normalized_property.latitude
        property_record.longitude = normalized_property.longitude
        property_record.normalized_property_json = serialize_model_snapshot(normalized_property)
        property_record.property_schema_version = SNAPSHOT_SCHEMA_VERSION_V1

    def _apply_verified_snapshot(
        self,
        property_record: PropertyRecord,
        verified_property: VerifiedPropertySnapshot,
    ) -> None:
        property_record.source_url = verified_property.source_url
        property_record.provider = verified_property.provider
        property_record.full_address = verified_property.full_address.final_value
        property_record.verified_property_json = serialize_model_snapshot(verified_property)
        property_record.verified_property_schema_version = SNAPSHOT_SCHEMA_VERSION_V1

    def _commit_refresh(self, property_record: PropertyRecord) -> None:
        try:
            self.session.commit()
            self.session.refresh(property_record)
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise DatabaseOperationError(message="Failed to persist property state.") from exc
