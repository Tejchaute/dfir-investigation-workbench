import uuid
from datetime import datetime

from pydantic import Field

from app.domain.enums import EvidenceType
from app.schemas.common import ReadSchema, TimezoneAwareSchema


class EvidenceCreate(TimezoneAwareSchema):
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
    original_path: str | None
    stored_path: str | None
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
