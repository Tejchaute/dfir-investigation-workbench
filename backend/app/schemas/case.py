import uuid
from datetime import datetime
from typing import Annotated

from pydantic import ConfigDict, Field, StringConstraints, model_validator

from app.domain.enums import CaseStatus
from app.schemas.common import ReadSchema, TimezoneAwareSchema

CaseName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]


class CaseCreate(TimezoneAwareSchema):
    model_config = ConfigDict(extra="forbid")

    name: CaseName
    description: str | None = None
    investigator: str | None = Field(default=None, max_length=255)


class CaseUpdate(TimezoneAwareSchema):
    model_config = ConfigDict(extra="forbid")

    name: CaseName | None = None
    description: str | None = None
    investigator: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def require_change(self) -> "CaseUpdate":
        if not self.model_fields_set:
            raise ValueError("at least one case field must be provided")
        return self


class CaseRead(ReadSchema):
    id: uuid.UUID
    case_number: str
    name: str
    description: str | None
    investigator: str | None
    status: CaseStatus
    created_at: datetime
    updated_at: datetime


class PaginationMeta(ReadSchema):
    limit: int
    offset: int
    total: int


class CaseListResponse(ReadSchema):
    data: list[CaseRead]
    meta: PaginationMeta
