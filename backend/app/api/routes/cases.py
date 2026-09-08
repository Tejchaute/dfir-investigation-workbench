import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.dependencies import DatabaseSession
from app.schemas.case import CaseCreate, CaseListResponse, CaseRead, CaseUpdate, PaginationMeta
from app.services.case_service import case_service

router = APIRouter(prefix="/cases", tags=["cases"])


@router.post("", response_model=CaseRead, status_code=status.HTTP_201_CREATED)
def create_case(payload: CaseCreate, session: DatabaseSession) -> CaseRead:
    return CaseRead.model_validate(case_service.create(session, payload))


@router.get("", response_model=CaseListResponse)
def list_cases(
    session: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> CaseListResponse:
    cases, total = case_service.list(session, limit=limit, offset=offset)
    return CaseListResponse(
        data=[CaseRead.model_validate(case) for case in cases],
        meta=PaginationMeta(limit=limit, offset=offset, total=total),
    )


@router.get("/{case_id}", response_model=CaseRead)
def get_case(case_id: uuid.UUID, session: DatabaseSession) -> CaseRead:
    return CaseRead.model_validate(case_service.get(session, case_id))


@router.patch("/{case_id}", response_model=CaseRead)
def update_case(case_id: uuid.UUID, payload: CaseUpdate, session: DatabaseSession) -> CaseRead:
    return CaseRead.model_validate(case_service.update(session, case_id, payload))


@router.post("/{case_id}/close", response_model=CaseRead)
def close_case(case_id: uuid.UUID, session: DatabaseSession) -> CaseRead:
    return CaseRead.model_validate(case_service.close(session, case_id))


@router.post("/{case_id}/archive", response_model=CaseRead)
def archive_case(case_id: uuid.UUID, session: DatabaseSession) -> CaseRead:
    return CaseRead.model_validate(case_service.archive(session, case_id))
