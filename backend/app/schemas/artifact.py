import uuid
from datetime import datetime

from pydantic import ConfigDict, Field

from app.domain.enums import ArtifactType, ParserExecutionStatus
from app.schemas.case import PaginationMeta
from app.schemas.common import ReadSchema


class ParseRequest(ReadSchema):
    model_config = ConfigDict(extra="forbid")

    artifact_type: ArtifactType


class ArtifactRead(ReadSchema):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    evidence_id: uuid.UUID
    artifact_type: ArtifactType
    parser_name: str
    parser_version: str
    status: ParserExecutionStatus
    metadata: dict[str, object] = Field(validation_alias="metadata_")
    warnings: list[str]
    errors: list[str]
    statistics: dict[str, int | float]
    record_count: int
    created_at: datetime


class ArtifactListResponse(ReadSchema):
    data: list[ArtifactRead]
    meta: PaginationMeta


class ArtifactRecordRead(ReadSchema):
    id: uuid.UUID
    artifact_id: uuid.UUID
    record_type: str
    source_record_identifier: str | None
    event_time: datetime | None
    data: dict[str, object]
    provenance: dict[str, object]
    created_at: datetime


class ArtifactRecordListResponse(ReadSchema):
    data: list[ArtifactRecordRead]
    meta: PaginationMeta
