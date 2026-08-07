"""Helpers for validated snapshot serialization and deserialization."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from pydantic import BaseModel

from app.exceptions import SnapshotValidationError

SNAPSHOT_SCHEMA_VERSION_V1 = "v1"


def serialize_model_snapshot(
    value: BaseModel,
    *,
    schema_version: str = SNAPSHOT_SCHEMA_VERSION_V1,
) -> dict[str, Any]:
    """Serialize a Pydantic model into a versioned JSON envelope."""

    return {
        "schema_version": schema_version,
        "data": value.model_dump(mode="json"),
    }


def serialize_mapping_snapshot(
    value: Mapping[str, Any],
    *,
    schema_version: str = SNAPSHOT_SCHEMA_VERSION_V1,
) -> dict[str, Any]:
    """Serialize a plain mapping into the shared versioned envelope."""

    return {
        "schema_version": schema_version,
        "data": dict(value),
    }


def deserialize_model_snapshot[ModelT: BaseModel](
    payload: Mapping[str, Any] | None,
    model_type: type[ModelT],
) -> ModelT | None:
    """Validate and deserialize a versioned JSON envelope into a model."""

    if payload is None:
        return None
    data = _snapshot_data(payload)
    return model_type.model_validate(data)


def deserialize_mapping_snapshot(payload: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Validate and return a plain mapping from a versioned envelope."""

    if payload is None:
        return None
    data = _snapshot_data(payload)
    if not isinstance(data, Mapping):
        raise SnapshotValidationError(message="Snapshot data must be a JSON object.")
    return dict(data)


def snapshot_schema_version(payload: Mapping[str, Any] | None) -> str | None:
    """Read the schema version from a versioned snapshot envelope."""

    if payload is None:
        return None
    version = payload.get("schema_version")
    if not isinstance(version, str) or not version:
        raise SnapshotValidationError(message="Snapshot schema_version is missing or invalid.")
    return version


def _snapshot_data(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    version = payload.get("schema_version")
    if not isinstance(version, str) or not version:
        raise SnapshotValidationError(message="Snapshot schema_version is missing or invalid.")
    data = payload.get("data")
    if not isinstance(data, Mapping):
        raise SnapshotValidationError(message="Snapshot data must be a JSON object.")
    return cast(Mapping[str, Any], data)
