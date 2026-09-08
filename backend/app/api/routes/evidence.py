import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, File, Form, Query, UploadFile, status

from app.api.dependencies import DatabaseSession
from app.domain.enums import EvidenceType
from app.schemas.case import PaginationMeta
from app.schemas.custody import ChainOfCustodyEntryRead
from app.schemas.evidence import (
    EvidenceHashRead,
    EvidenceListResponse,
    EvidenceRead,
    EvidenceRegistration,
    EvidenceVerificationRead,
)
from app.services.evidence_service import evidence_service

case_evidence_router = APIRouter(prefix="/cases/{case_id}/evidence", tags=["evidence"])
evidence_router = APIRouter(prefix="/evidence", tags=["evidence"])


@case_evidence_router.post("", response_model=EvidenceRead, status_code=status.HTTP_201_CREATED)
def register_evidence(
    case_id: uuid.UUID,
    session: DatabaseSession,
    file: Annotated[UploadFile, File()],
    evidence_type: Annotated[EvidenceType, Form()],
    custody_person: Annotated[str, Form(min_length=1, max_length=255)],
    description: Annotated[str | None, Form()] = None,
    collected_by: Annotated[str | None, Form(max_length=255)] = None,
    collected_at: Annotated[datetime | None, Form()] = None,
    custody_location: Annotated[str | None, Form(max_length=500)] = None,
    custody_notes: Annotated[str | None, Form()] = None,
) -> EvidenceRead:
    payload = EvidenceRegistration(
        description=description,
        evidence_type=evidence_type,
        collected_by=collected_by,
        collected_at=collected_at,
        custody_person=custody_person,
        custody_location=custody_location,
        custody_notes=custody_notes,
    )
    return EvidenceRead.model_validate(
        evidence_service.register(session, case_id, file.filename, file.file, payload)
    )


@case_evidence_router.get("", response_model=EvidenceListResponse)
def list_evidence(
    case_id: uuid.UUID,
    session: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> EvidenceListResponse:
    items, total = evidence_service.list_for_case(session, case_id, limit=limit, offset=offset)
    return EvidenceListResponse(
        data=[EvidenceRead.model_validate(item) for item in items],
        meta=PaginationMeta(limit=limit, offset=offset, total=total),
    )


@evidence_router.get("/{evidence_id}", response_model=EvidenceRead)
def get_evidence(evidence_id: uuid.UUID, session: DatabaseSession) -> EvidenceRead:
    return EvidenceRead.model_validate(evidence_service.get(session, evidence_id))


@evidence_router.get("/{evidence_id}/hashes", response_model=list[EvidenceHashRead])
def get_evidence_hashes(evidence_id: uuid.UUID, session: DatabaseSession) -> list[EvidenceHashRead]:
    return [
        EvidenceHashRead.model_validate(item)
        for item in evidence_service.hashes(session, evidence_id)
    ]


@evidence_router.get("/{evidence_id}/coc", response_model=list[ChainOfCustodyEntryRead])
def get_chain_of_custody(
    evidence_id: uuid.UUID, session: DatabaseSession
) -> list[ChainOfCustodyEntryRead]:
    return [
        ChainOfCustodyEntryRead.model_validate(item)
        for item in evidence_service.custody(session, evidence_id)
    ]


@evidence_router.post("/{evidence_id}/verify", response_model=EvidenceVerificationRead)
def verify_evidence(evidence_id: uuid.UUID, session: DatabaseSession) -> EvidenceVerificationRead:
    return evidence_service.verify(session, evidence_id)
