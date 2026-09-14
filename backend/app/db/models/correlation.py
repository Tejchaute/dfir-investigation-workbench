from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins import TimestampMixin
from app.domain.enums import (
    CorrelationRunStatus,
    FindingConfidence,
    FindingSeverity,
    FindingStatus,
    FindingType,
)

if TYPE_CHECKING:
    from app.db.models.case import Case
    from app.db.models.timeline import TimelineEvent


class CorrelationRun(Base):
    __tablename__ = "correlation_runs"
    __table_args__ = (
        Index("ix_correlation_runs_case_id", "case_id"),
        Index("ix_correlation_runs_status", "status"),
        Index("ix_correlation_runs_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cases.id", ondelete="RESTRICT"), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[CorrelationRunStatus] = mapped_column(
        Enum(
            CorrelationRunStatus,
            name="correlation_run_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
    )
    rule_set_version: Mapped[str] = mapped_column(String(100), nullable=False)
    temporal_window_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    event_count: Mapped[int] = mapped_column(Integer, nullable=False)
    matched_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    finding_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rules_evaluated: Mapped[list[dict[str, str]]] = mapped_column(JSONB, nullable=False)
    warnings: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    errors: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    case: Mapped[Case] = relationship()
    matches: Mapped[list[CorrelationMatch]] = relationship(
        back_populates="correlation_run", passive_deletes=True
    )
    findings: Mapped[list[Finding]] = relationship(
        back_populates="correlation_run", passive_deletes=True
    )


class CorrelationMatch(Base):
    __tablename__ = "correlation_matches"
    __table_args__ = (
        Index("ix_correlation_matches_case_id", "case_id"),
        Index("ix_correlation_matches_run_id", "correlation_run_id"),
        Index("ix_correlation_matches_rule", "rule_id", "rule_version"),
        Index("ix_correlation_matches_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    correlation_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("correlation_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cases.id", ondelete="RESTRICT"), nullable=False
    )
    rule_id: Mapped[str] = mapped_column(String(100), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(50), nullable=False)
    deterministic_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    temporal_delta_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    match_basis: Mapped[str] = mapped_column(String(50), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict[str, object]] = mapped_column("metadata", JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    correlation_run: Mapped[CorrelationRun] = relationship(back_populates="matches")
    case: Mapped[Case] = relationship()
    event_links: Mapped[list[CorrelationMatchEvent]] = relationship(
        back_populates="correlation_match", passive_deletes=True
    )
    finding: Mapped[Finding | None] = relationship(
        back_populates="correlation_match", passive_deletes=True
    )


class CorrelationMatchEvent(Base):
    __tablename__ = "correlation_match_events"
    __table_args__ = (
        UniqueConstraint(
            "correlation_match_id",
            "timeline_event_id",
            name="uq_correlation_match_event",
        ),
        Index("ix_correlation_match_events_match_id", "correlation_match_id"),
        Index("ix_correlation_match_events_event_id", "timeline_event_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    correlation_match_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("correlation_matches.id", ondelete="RESTRICT"),
        nullable=False,
    )
    timeline_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("timeline_events.id", ondelete="RESTRICT"),
        nullable=False,
    )
    event_role: Mapped[str] = mapped_column(String(50), nullable=False)
    event_order: Mapped[int] = mapped_column(Integer, nullable=False)

    correlation_match: Mapped[CorrelationMatch] = relationship(back_populates="event_links")
    timeline_event: Mapped[TimelineEvent] = relationship()


class Finding(TimestampMixin, Base):
    __tablename__ = "findings"
    __table_args__ = (
        Index("ix_findings_case_id", "case_id"),
        Index("ix_findings_run_id", "correlation_run_id"),
        Index("ix_findings_type", "finding_type"),
        Index("ix_findings_status", "status"),
        Index("ix_findings_severity", "severity"),
        Index("ix_findings_confidence", "confidence"),
        Index("ix_findings_rule", "rule_id", "rule_version"),
        Index("ix_findings_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cases.id", ondelete="RESTRICT"), nullable=False
    )
    correlation_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("correlation_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    correlation_match_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("correlation_matches.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    finding_type: Mapped[FindingType] = mapped_column(
        Enum(
            FindingType,
            name="finding_type",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[FindingStatus] = mapped_column(
        Enum(
            FindingStatus,
            name="finding_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
        default=FindingStatus.OPEN,
    )
    severity: Mapped[FindingSeverity] = mapped_column(
        Enum(
            FindingSeverity,
            name="finding_severity",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
    )
    confidence: Mapped[FindingConfidence] = mapped_column(
        Enum(
            FindingConfidence,
            name="finding_confidence",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
    )
    rule_id: Mapped[str] = mapped_column(String(100), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(50), nullable=False)
    deterministic_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    analyst_notes: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict[str, object]] = mapped_column("metadata", JSONB, nullable=False)

    case: Mapped[Case] = relationship()
    correlation_run: Mapped[CorrelationRun] = relationship(back_populates="findings")
    correlation_match: Mapped[CorrelationMatch] = relationship(back_populates="finding")
