"""SQLAlchemy ORM model for persisted properties."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import UTCDateTime

if TYPE_CHECKING:
    from app.db.models.analysis import AnalysisRecord


class PropertyRecord(Base):
    """Current persisted property state plus verified snapshot JSON."""

    __tablename__ = "properties"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    listing_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    full_address: Mapped[str | None] = mapped_column(String(512), nullable=True, index=True)
    street: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    state: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    postal_code: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    normalized_property_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    verified_property_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    property_schema_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")
    verified_property_schema_version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="v1",
    )
    current_version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    analyses: Mapped[list[AnalysisRecord]] = relationship(
        back_populates="property",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
