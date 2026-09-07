import uuid
from datetime import datetime

from pydantic import Field

from app.domain.enums import CaseStatus
from app.schemas.common import ReadSchema, TimezoneAwareSchema


class CaseCreate(TimezoneAwareSchema):
    case_number: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    investigator: str | None = Field(default=None, max_length=255)
    status: CaseStatus = CaseStatus.OPEN


class CaseUpdate(TimezoneAwareSchema):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    investigator: str | None = Field(default=None, max_length=255)
    status: CaseStatus | None = None


class CaseRead(ReadSchema):
    id: uuid.UUID
    case_number: str
    name: str
    description: str | None
    investigator: str | None
    status: CaseStatus
    created_at: datetime
    updated_at: datetime
