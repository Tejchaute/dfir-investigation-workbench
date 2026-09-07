from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins import TimestampMixin
from app.domain.enums import CaseStatus

if TYPE_CHECKING:
    from app.db.models.audit import AuditEvent
    from app.db.models.evidence import Evidence


class Case(TimestampMixin, Base):
    __tablename__ = "cases"
    __table_args__ = (Index("ix_cases_status", "status"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_number: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    investigator: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[CaseStatus] = mapped_column(
        Enum(
            CaseStatus,
            name="case_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
        default=CaseStatus.OPEN,
        server_default=CaseStatus.OPEN.value,
    )

    evidence_items: Mapped[list[Evidence]] = relationship(
        back_populates="case", passive_deletes=True
    )
    audit_events: Mapped[list[AuditEvent]] = relationship(
        back_populates="case", passive_deletes=True
    )
