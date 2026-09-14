import uuid
from datetime import datetime

from pydantic import ConfigDict, Field, model_validator

from app.domain.enums import (
    ArtifactType,
    CorrelationRunStatus,
    FindingConfidence,
    FindingSeverity,
    FindingStatus,
    FindingType,
    TimelineEventType,
)
from app.schemas.case import PaginationMeta
from app.schemas.common import ReadSchema


class CorrelationRunRead(ReadSchema):
    id: uuid.UUID
    case_id: uuid.UUID
    started_at: datetime
    completed_at: datetime | None
    status: CorrelationRunStatus
    rule_set_version: str
    temporal_window_seconds: int
    event_count: int
    matched_count: int
    finding_count: int
    rules_evaluated: list[dict[str, str]]
    warnings: list[str]
    errors: list[str]
    created_at: datetime


class SupportingTimelineEventRead(ReadSchema):
    id: uuid.UUID
    evidence_id: uuid.UUID
    artifact_id: uuid.UUID
    artifact_record_id: uuid.UUID
    artifact_type: ArtifactType
    event_type: TimelineEventType
    event_time: datetime | None
    source_identifier: str | None
    metadata: dict[str, object]
    provenance: dict[str, object]


class CorrelationMatchRead(ReadSchema):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    correlation_run_id: uuid.UUID
    case_id: uuid.UUID
    rule_id: str
    rule_version: str
    deterministic_key: str
    temporal_delta_seconds: float
    match_basis: str
    explanation: str
    metadata: dict[str, object] = Field(validation_alias="metadata_")
    timeline_event_ids: list[uuid.UUID]
    supporting_events: list[SupportingTimelineEventRead]
    created_at: datetime


class CorrelationMatchListResponse(ReadSchema):
    data: list[CorrelationMatchRead]
    meta: PaginationMeta


class FindingRead(ReadSchema):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    case_id: uuid.UUID
    correlation_run_id: uuid.UUID
    correlation_match_id: uuid.UUID
    finding_type: FindingType
    title: str
    description: str
    status: FindingStatus
    severity: FindingSeverity
    confidence: FindingConfidence
    rule_id: str
    rule_version: str
    deterministic_key: str
    analyst_notes: str | None
    metadata: dict[str, object] = Field(validation_alias="metadata_")
    timeline_event_ids: list[uuid.UUID]
    supporting_events: list[SupportingTimelineEventRead]
    created_at: datetime
    updated_at: datetime


class FindingListResponse(ReadSchema):
    data: list[FindingRead]
    meta: PaginationMeta


class FindingUpdate(ReadSchema):
    model_config = ConfigDict(extra="forbid")

    status: FindingStatus | None = None
    severity: FindingSeverity | None = None
    confidence: FindingConfidence | None = None
    analyst_notes: str | None = Field(default=None, max_length=20_000)

    @model_validator(mode="after")
    def require_change(self) -> "FindingUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one finding field must be supplied")
        return self
