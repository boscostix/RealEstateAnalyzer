"""SQLAlchemy ORM model for persisted analyses."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import JSON, Enum, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import UTCDateTime

if TYPE_CHECKING:
    from app.db.models.property import PropertyRecord


def _enum_values(enum_cls: type[StrEnum]) -> list[str]:
    return [member.value for member in enum_cls]


class AnalysisStatus(StrEnum):
    """Allowed persisted lifecycle states for an analysis."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisStage(StrEnum):
    """Pipeline stages used for persisted progress tracking."""

    PREPARATION = "preparation"
    UNDERWRITING = "underwriting"
    RESEARCH = "research"
    AGENT_RESEARCH = "agent_research"
    INVESTMENT_COMMITTEE = "investment_committee"
    PERSISTENCE = "persistence"


class AnalysisRecord(Base):
    """Immutable analysis snapshots and lifecycle metadata."""

    __tablename__ = "analyses"
    __table_args__ = (
        UniqueConstraint("property_id", "version", name="uq_analyses_property_version"),
        Index("ix_analyses_property_created", "property_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    property_id: Mapped[str] = mapped_column(
        ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_analysis_id: Mapped[str | None] = mapped_column(
        ForeignKey("analyses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    version: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[AnalysisStatus] = mapped_column(
        Enum(AnalysisStatus, native_enum=False, values_callable=_enum_values),
        nullable=False,
        default=AnalysisStatus.PENDING,
        index=True,
    )
    current_stage: Mapped[AnalysisStage | None] = mapped_column(
        Enum(AnalysisStage, native_enum=False, values_callable=_enum_values),
        nullable=True,
    )
    failure_stage: Mapped[AnalysisStage | None] = mapped_column(
        Enum(AnalysisStage, native_enum=False, values_callable=_enum_values),
        nullable=True,
    )
    property_snapshot_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    assumptions_snapshot_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    underwriting_result_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    research_result_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    agent_research_result_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    investment_committee_result_json: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    execution_metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    analysis_schema_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")
    report_schema_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")
    error_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)

    property: Mapped[PropertyRecord] = relationship(back_populates="analyses")
    parent_analysis: Mapped[AnalysisRecord | None] = relationship(
        remote_side="AnalysisRecord.id",
        back_populates="reruns",
    )
    reruns: Mapped[list[AnalysisRecord]] = relationship(back_populates="parent_analysis")
