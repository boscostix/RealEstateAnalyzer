"""Persistence-oriented property service for Milestone 6."""

from __future__ import annotations

from app.db.analysis_persistence import deserialize_property_record
from app.db.models import PropertyRecord
from app.db.repositories.property_repository import PropertyRepository
from app.models.property import NormalizedProperty
from app.models.verification import VerifiedPropertySnapshot


class PropertyService:
    """Application-level operations for current persisted property state."""

    def __init__(self, repository: PropertyRepository) -> None:
        self.repository = repository

    def create_property(
        self,
        *,
        normalized_property: NormalizedProperty | None = None,
        verified_property: VerifiedPropertySnapshot | None = None,
    ) -> PropertyRecord:
        return self.repository.create(
            normalized_property=normalized_property,
            verified_property=verified_property,
        )

    def get_property(self, property_id: str) -> PropertyRecord:
        return self.repository.get_required_by_id(property_id)

    def get_property_snapshots(
        self,
        property_id: str,
    ) -> tuple[NormalizedProperty | None, VerifiedPropertySnapshot | None]:
        property_record = self.repository.get_required_by_id(property_id)
        return deserialize_property_record(property_record)

    def update_property(
        self,
        property_id: str,
        *,
        normalized_property: NormalizedProperty | None = None,
        verified_property: VerifiedPropertySnapshot | None = None,
        current_version: int | None = None,
    ) -> PropertyRecord:
        return self.repository.update(
            property_id,
            normalized_property=normalized_property,
            verified_property=verified_property,
            current_version=current_version,
        )
