import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.common import ReadSchema, TimezoneAwareSchema


class ChainOfCustodyEntryCreate(TimezoneAwareSchema):
    timestamp: datetime
    person: str = Field(min_length=1, max_length=255)
    action: str = Field(min_length=1, max_length=100)
    location: str | None = Field(default=None, max_length=500)
    notes: str | None = None


class ChainOfCustodyEntryRead(ReadSchema):
    id: uuid.UUID
    evidence_id: uuid.UUID
    timestamp: datetime
    person: str
    action: str
    location: str | None
    notes: str | None
    created_at: datetime
