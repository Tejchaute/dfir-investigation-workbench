from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.enums import ArtifactType, ParserExecutionStatus

if TYPE_CHECKING:
    from app.db.models.evidence import Evidence


class Artifact(Base):
    __tablename__ = "artifacts"
    __table_args__ = (
        Index("ix_artifacts_evidence_id", "evidence_id"),
        Index("ix_artifacts_artifact_type", "artifact_type"),
        Index("ix_artifacts_status", "status"),
        Index("ix_artifacts_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evidence.id", ondelete="RESTRICT"), nullable=False
    )
    artifact_type: Mapped[ArtifactType] = mapped_column(
        Enum(
            ArtifactType,
            name="artifact_type",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
    )
    parser_name: Mapped[str] = mapped_column(String(255), nullable=False)
    parser_version: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[ParserExecutionStatus] = mapped_column(
        Enum(
            ParserExecutionStatus,
            name="parser_execution_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
    )
    metadata_: Mapped[dict[str, object]] = mapped_column("metadata", JSONB, nullable=False)
    warnings: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    errors: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    statistics: Mapped[dict[str, int | float]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    evidence: Mapped[Evidence] = relationship(back_populates="artifacts")
    records: Mapped[list[ArtifactRecord]] = relationship(
        back_populates="artifact", passive_deletes=True
    )


class ArtifactRecord(Base):
    __tablename__ = "artifact_records"
    __table_args__ = (
        Index("ix_artifact_records_artifact_id", "artifact_id"),
        Index("ix_artifact_records_event_time", "event_time"),
        Index("ix_artifact_records_record_type", "record_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("artifacts.id", ondelete="RESTRICT"), nullable=False
    )
    record_type: Mapped[str] = mapped_column(String(255), nullable=False)
    source_record_identifier: Mapped[str | None] = mapped_column(String(500))
    event_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    data: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    provenance: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    artifact: Mapped[Artifact] = relationship(back_populates="records")
