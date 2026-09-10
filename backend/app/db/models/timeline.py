from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import ArtifactType, TimelineEventType, TimestampPrecision

if TYPE_CHECKING:
    from app.db.models.artifact import Artifact, ArtifactRecord
    from app.db.models.case import Case
    from app.db.models.evidence import Evidence


class TimelineEvent(Base):
    __tablename__ = "timeline_events"
    __table_args__ = (
        UniqueConstraint(
            "artifact_record_id",
            "event_type",
            "time_source",
            "event_ordinal",
            name="uq_timeline_events_logical_identity",
        ),
        Index("ix_timeline_events_case_id", "case_id"),
        Index("ix_timeline_events_evidence_id", "evidence_id"),
        Index("ix_timeline_events_artifact_id", "artifact_id"),
        Index("ix_timeline_events_artifact_record_id", "artifact_record_id"),
        Index("ix_timeline_events_event_time", "event_time"),
        Index("ix_timeline_events_event_type", "event_type"),
        Index("ix_timeline_events_artifact_type", "artifact_type"),
        Index("ix_timeline_events_source_identifier", "source_identifier"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cases.id", ondelete="RESTRICT"), nullable=False
    )
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evidence.id", ondelete="RESTRICT"), nullable=False
    )
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("artifacts.id", ondelete="RESTRICT"), nullable=False
    )
    artifact_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("artifact_records.id", ondelete="RESTRICT"), nullable=False
    )
    parser_name: Mapped[str] = mapped_column(String(255), nullable=False)
    parser_version: Mapped[str] = mapped_column(String(100), nullable=False)
    artifact_type: Mapped[ArtifactType] = mapped_column(
        Enum(
            ArtifactType,
            name="timeline_artifact_type",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
    )
    event_type: Mapped[TimelineEventType] = mapped_column(
        Enum(
            TimelineEventType,
            name="timeline_event_type",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
    )
    event_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    raw_time: Mapped[str | None] = mapped_column(String(255))
    time_source: Mapped[str] = mapped_column(String(255), nullable=False)
    time_semantics: Mapped[str] = mapped_column(String(255), nullable=False)
    timestamp_precision: Mapped[TimestampPrecision] = mapped_column(
        Enum(
            TimestampPrecision,
            name="timestamp_precision",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda values: [item.value for item in values],
        ),
        nullable=False,
    )
    event_ordinal: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    description: Mapped[str] = mapped_column(String(1000), nullable=False)
    source_identifier: Mapped[str | None] = mapped_column(String(500))
    metadata_: Mapped[dict[str, object]] = mapped_column("metadata", JSONB, nullable=False)
    provenance: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    case: Mapped[Case] = relationship()
    evidence: Mapped[Evidence] = relationship()
    artifact: Mapped[Artifact] = relationship(back_populates="timeline_events")
    artifact_record: Mapped[ArtifactRecord] = relationship(back_populates="timeline_events")
