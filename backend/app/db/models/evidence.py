from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins import TimestampMixin
from app.domain.enums import EvidenceType

if TYPE_CHECKING:
    from app.db.models.audit import AuditEvent
    from app.db.models.case import Case
    from app.db.models.custody import ChainOfCustodyEntry


class Evidence(TimestampMixin, Base):
    __tablename__ = "evidence"
    __table_args__ = (
        UniqueConstraint("case_id", "evidence_number", name="uq_evidence_case_number"),
        Index("ix_evidence_case_id", "case_id"),
        Index("ix_evidence_type", "evidence_type"),
        Index("ix_evidence_number", "evidence_number"),
        CheckConstraint(
            "size_bytes IS NULL OR size_bytes >= 0", name="ck_evidence_size_nonnegative"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cases.id", ondelete="RESTRICT"), nullable=False
    )
    evidence_number: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    evidence_type: Mapped[EvidenceType] = mapped_column(
        Enum(
            EvidenceType,
            name="evidence_type",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
    )
    original_path: Mapped[str | None] = mapped_column(Text)
    stored_path: Mapped[str | None] = mapped_column(Text)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    collected_by: Mapped[str | None] = mapped_column(String(255))
    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    case: Mapped[Case] = relationship(back_populates="evidence_items")
    hashes: Mapped[list[EvidenceHash]] = relationship(
        back_populates="evidence", passive_deletes=True
    )
    custody_entries: Mapped[list[ChainOfCustodyEntry]] = relationship(
        back_populates="evidence", passive_deletes=True
    )
    audit_events: Mapped[list[AuditEvent]] = relationship(
        back_populates="evidence", passive_deletes=True
    )


class EvidenceHash(Base):
    __tablename__ = "evidence_hashes"
    __table_args__ = (
        Index("ix_evidence_hashes_evidence_id", "evidence_id"),
        Index("ix_evidence_hashes_algorithm", "algorithm"),
        Index("ix_evidence_hashes_computed_at", "computed_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evidence.id", ondelete="RESTRICT"), nullable=False
    )
    algorithm: Mapped[str] = mapped_column(String(32), nullable=False)
    digest: Mapped[str] = mapped_column(String(256), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    purpose: Mapped[str] = mapped_column(String(100), nullable=False)

    evidence: Mapped[Evidence] = relationship(back_populates="hashes")
