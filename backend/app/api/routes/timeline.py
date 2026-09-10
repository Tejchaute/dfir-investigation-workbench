import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencies import DatabaseSession
from app.domain.enums import ArtifactType, TimelineEventType
from app.schemas.case import PaginationMeta
from app.schemas.timeline import (
    TimelineEventListResponse,
    TimelineEventRead,
    TimelineGenerationRead,
)
from app.services.timeline_service import timeline_service

router = APIRouter(prefix="/cases/{case_id}/timeline", tags=["timeline"])


@router.post("/generate", response_model=TimelineGenerationRead)
def generate_timeline(case_id: uuid.UUID, session: DatabaseSession) -> TimelineGenerationRead:
    result = timeline_service.generate(session, case_id)
    return TimelineGenerationRead(
        case_id=result.case_id,
        artifacts_considered=result.artifacts_considered,
        records_considered=result.records_considered,
        events_created=result.events_created,
        events_skipped=result.events_skipped,
        warnings=result.warnings,
        unsupported_artifact_types=result.unsupported_artifact_types,
    )


@router.get("", response_model=TimelineEventListResponse)
def list_timeline(
    case_id: uuid.UUID,
    session: DatabaseSession,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    event_type: TimelineEventType | None = None,
    artifact_type: ArtifactType | None = None,
    evidence_id: uuid.UUID | None = None,
    source_identifier: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TimelineEventListResponse:
    events, total = timeline_service.list_events(
        session,
        case_id,
        start_time=start_time,
        end_time=end_time,
        event_type=event_type,
        artifact_type=artifact_type,
        evidence_id=evidence_id,
        source_identifier=source_identifier,
        limit=limit,
        offset=offset,
    )
    return TimelineEventListResponse(
        data=[TimelineEventRead.model_validate(event) for event in events],
        meta=PaginationMeta(limit=limit, offset=offset, total=total),
    )
