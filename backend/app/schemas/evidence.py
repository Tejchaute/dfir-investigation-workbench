import uuid
from datetime import datetime
from typing import Annotated

from pydantic import ConfigDict, Field, StringConstraints

from app.domain.enums import EvidenceType
from app.schemas.case import PaginationMeta
from app.schemas.common import ReadSchema, TimezoneAwareSchema


class EvidenceRegistration(TimezoneAwareSchema):
    model_config = ConfigDict(extra="forbid")

    description: str | None = None
    evidence_type: EvidenceType
    collected_by: str | None = Field(default=None, max_length=255)
    collected_at: datetime | None = None
    custody_person: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
    ]
    custody_location: str | None = Field(default=None, max_length=500)
    custody_notes: str | None = None


class EvidenceCreate(TimezoneAwareSchema):
    """Internal Phase 1 metadata schema; not accepted by the upload API."""

    evidence_number: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    evidence_type: EvidenceType
    original_path: str | None = None
    stored_path: str | None = None
    size_bytes: int | None = Field(default=None, ge=0)
    collected_by: str | None = Field(default=None, max_length=255)
    collected_at: datetime | None = None


class EvidenceUpdate(TimezoneAwareSchema):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    evidence_type: EvidenceType | None = None
    original_path: str | None = None
    stored_path: str | None = None
    size_bytes: int | None = Field(default=None, ge=0)
    collected_by: str | None = Field(default=None, max_length=255)
    collected_at: datetime | None = None


class EvidenceRead(ReadSchema):
    id: uuid.UUID
    case_id: uuid.UUID
    evidence_number: str
    name: str
    description: str | None
    evidence_type: EvidenceType
    size_bytes: int | None
    collected_by: str | None
    collected_at: datetime | None
    created_at: datetime
    updated_at: datetime


class EvidenceHashRead(ReadSchema):
    id: uuid.UUID
    evidence_id: uuid.UUID
    algorithm: str
    digest: str
    computed_at: datetime
    purpose: str


class EvidenceListResponse(ReadSchema):
    data: list[EvidenceRead]
    meta: "PaginationMeta"


class EvidenceVerificationRead(ReadSchema):
    evidence_id: uuid.UUID
    algorithm: str
    recorded_digest: str
    calculated_digest: str
    match: bool
    verified_at: datetime
