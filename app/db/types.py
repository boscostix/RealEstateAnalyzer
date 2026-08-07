"""Shared SQLAlchemy column types for persistence models."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.types import DateTime, TypeDecorator


class UTCDateTime(TypeDecorator[datetime]):
    """Store datetimes in UTC and always return timezone-aware values."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: object) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("UTCDateTime values must be timezone-aware.")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect: object) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
