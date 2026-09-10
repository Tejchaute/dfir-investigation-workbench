import uuid
from datetime import datetime

from pydantic import ConfigDict, Field

from app.domain.enums import ArtifactType, TimelineEventType, TimestampPrecision
from app.schemas.case import PaginationMeta
from app.schemas.common import ReadSchema


class TimelineGenerationRead(ReadSchema):
    case_id: uuid.UUID
    artifacts_considered: int
    records_considered: int
    events_created: int
    events_skipped: int
    warnings: list[str]
    unsupported_artifact_types: list[ArtifactType]


class TimelineEventRead(ReadSchema):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    case_id: uuid.UUID
    evidence_id: uuid.UUID
    artifact_id: uuid.UUID
    artifact_record_id: uuid.UUID
    parser_name: str
    parser_version: str
    artifact_type: ArtifactType
    event_type: TimelineEventType
    event_time: datetime | None
    raw_time: str | None
    time_source: str
    time_semantics: str
    timestamp_precision: TimestampPrecision
    event_ordinal: int
    description: str
    source_identifier: str | None
    metadata: dict[str, object] = Field(validation_alias="metadata_")
    provenance: dict[str, object]
    created_at: datetime


class TimelineEventListResponse(ReadSchema):
    data: list[TimelineEventRead]
    meta: PaginationMeta
