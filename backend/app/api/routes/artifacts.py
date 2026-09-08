import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencies import DatabaseSession
from app.db.models import Artifact
from app.schemas.artifact import (
    ArtifactListResponse,
    ArtifactRead,
    ArtifactRecordListResponse,
    ArtifactRecordRead,
    ParseRequest,
)
from app.schemas.case import PaginationMeta
from app.services.parser_execution_service import parser_execution_service

evidence_artifact_router = APIRouter(prefix="/evidence/{evidence_id}", tags=["artifacts"])
artifact_router = APIRouter(prefix="/artifacts", tags=["artifacts"])


def _artifact_read(artifact: Artifact, record_count: int) -> ArtifactRead:
    return ArtifactRead(
        id=artifact.id,
        evidence_id=artifact.evidence_id,
        artifact_type=artifact.artifact_type,
        parser_name=artifact.parser_name,
        parser_version=artifact.parser_version,
        status=artifact.status,
        metadata=artifact.metadata_,
        warnings=artifact.warnings,
        errors=artifact.errors,
        statistics=artifact.statistics,
        record_count=record_count,
        created_at=artifact.created_at,
    )


@evidence_artifact_router.post("/parse", response_model=ArtifactRead)
def parse_evidence(
    evidence_id: uuid.UUID, payload: ParseRequest, session: DatabaseSession
) -> ArtifactRead:
    artifact, record_count = parser_execution_service.execute(
        session, evidence_id, payload.artifact_type
    )
    return _artifact_read(artifact, record_count)


@evidence_artifact_router.get("/artifacts", response_model=ArtifactListResponse)
def list_artifacts(
    evidence_id: uuid.UUID,
    session: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ArtifactListResponse:
    rows, total = parser_execution_service.list_for_evidence(
        session, evidence_id, limit=limit, offset=offset
    )
    return ArtifactListResponse(
        data=[_artifact_read(artifact, count) for artifact, count in rows],
        meta=PaginationMeta(limit=limit, offset=offset, total=total),
    )


@artifact_router.get("/{artifact_id}", response_model=ArtifactRead)
def get_artifact(artifact_id: uuid.UUID, session: DatabaseSession) -> ArtifactRead:
    artifact, count = parser_execution_service.get(session, artifact_id)
    return _artifact_read(artifact, count)


@artifact_router.get("/{artifact_id}/records", response_model=ArtifactRecordListResponse)
def list_artifact_records(
    artifact_id: uuid.UUID,
    session: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ArtifactRecordListResponse:
    records, total = parser_execution_service.records(
        session, artifact_id, limit=limit, offset=offset
    )
    return ArtifactRecordListResponse(
        data=[ArtifactRecordRead.model_validate(record) for record in records],
        meta=PaginationMeta(limit=limit, offset=offset, total=total),
    )
