import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencies import DatabaseSession
from app.domain.enums import FindingConfidence, FindingSeverity, FindingStatus
from app.schemas.case import PaginationMeta
from app.schemas.correlation import (
    CorrelationMatchListResponse,
    CorrelationMatchRead,
    CorrelationRunRead,
    FindingListResponse,
    FindingRead,
    FindingUpdate,
)
from app.services.correlation_service import correlation_service

case_router = APIRouter(prefix="/cases/{case_id}", tags=["correlation", "findings"])
finding_router = APIRouter(prefix="/findings", tags=["findings"])


@case_router.post("/correlation/run", response_model=CorrelationRunRead)
def run_correlation(case_id: uuid.UUID, session: DatabaseSession) -> CorrelationRunRead:
    return CorrelationRunRead.model_validate(correlation_service.run(session, case_id))


@case_router.get("/correlations", response_model=CorrelationMatchListResponse)
def list_correlations(
    case_id: uuid.UUID,
    session: DatabaseSession,
    rule_id: str | None = None,
    correlation_run_id: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> CorrelationMatchListResponse:
    matches, total = correlation_service.list_matches(
        session,
        case_id,
        rule_id=rule_id,
        correlation_run_id=correlation_run_id,
        limit=limit,
        offset=offset,
    )
    return CorrelationMatchListResponse(
        data=[_match_read(match) for match in matches],
        meta=PaginationMeta(limit=limit, offset=offset, total=total),
    )


@case_router.get("/findings", response_model=FindingListResponse)
def list_findings(
    case_id: uuid.UUID,
    session: DatabaseSession,
    status: FindingStatus | None = None,
    severity: FindingSeverity | None = None,
    confidence: FindingConfidence | None = None,
    rule_id: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> FindingListResponse:
    findings, total = correlation_service.list_findings(
        session,
        case_id,
        status=status,
        severity=severity,
        confidence=confidence,
        rule_id=rule_id,
        limit=limit,
        offset=offset,
    )
    return FindingListResponse(
        data=[_finding_read(finding) for finding in findings],
        meta=PaginationMeta(limit=limit, offset=offset, total=total),
    )


@finding_router.get("/{finding_id}", response_model=FindingRead)
def get_finding(finding_id: uuid.UUID, session: DatabaseSession) -> FindingRead:
    return _finding_read(correlation_service.get_finding(session, finding_id))


@finding_router.patch("/{finding_id}", response_model=FindingRead)
def update_finding(
    finding_id: uuid.UUID, payload: FindingUpdate, session: DatabaseSession
) -> FindingRead:
    return _finding_read(correlation_service.update_finding(session, finding_id, payload))


def _match_read(match: object) -> CorrelationMatchRead:
    from app.db.models import CorrelationMatch

    assert isinstance(match, CorrelationMatch)
    data = CorrelationMatchRead.model_validate(
        {
            **{
                column.name: getattr(match, column.key)
                for column in CorrelationMatch.__table__.columns
            },
            "metadata": match.metadata_,
            "timeline_event_ids": [
                link.timeline_event_id
                for link in sorted(match.event_links, key=lambda item: item.event_order)
            ],
            "supporting_events": [
                _supporting_event(link.timeline_event)
                for link in sorted(match.event_links, key=lambda item: item.event_order)
            ],
        }
    )
    return data


def _finding_read(finding: object) -> FindingRead:
    from app.db.models import Finding

    assert isinstance(finding, Finding)
    return FindingRead.model_validate(
        {
            **{column.name: getattr(finding, column.key) for column in Finding.__table__.columns},
            "metadata": finding.metadata_,
            "timeline_event_ids": [
                link.timeline_event_id
                for link in sorted(
                    finding.correlation_match.event_links, key=lambda item: item.event_order
                )
            ],
            "supporting_events": [
                _supporting_event(link.timeline_event)
                for link in sorted(
                    finding.correlation_match.event_links, key=lambda item: item.event_order
                )
            ],
        }
    )


def _supporting_event(event: object) -> dict[str, object]:
    from app.db.models import TimelineEvent

    assert isinstance(event, TimelineEvent)
    return {
        "id": event.id,
        "evidence_id": event.evidence_id,
        "artifact_id": event.artifact_id,
        "artifact_record_id": event.artifact_record_id,
        "artifact_type": event.artifact_type,
        "event_type": event.event_type,
        "event_time": event.event_time,
        "source_identifier": event.source_identifier,
        "metadata": event.metadata_,
        "provenance": event.provenance,
    }
