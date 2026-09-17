import uuid
from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse

from app.api.dependencies import DatabaseSession
from app.domain.enums import ReportFormat
from app.schemas.case import PaginationMeta
from app.schemas.report import ReportCreate, ReportListResponse, ReportRead
from app.services.report_service import report_service

case_router = APIRouter(prefix="/cases/{case_id}/reports", tags=["reports"])
report_router = APIRouter(prefix="/reports", tags=["reports"])


@case_router.post("", response_model=ReportRead, status_code=201)
def generate_report(
    case_id: uuid.UUID, payload: ReportCreate, session: DatabaseSession
) -> ReportRead:
    report = report_service.generate(
        session,
        case_id,
        report_format=payload.format,
        report_type=payload.report_type,
    )
    return ReportRead.model_validate(report)


@case_router.get("", response_model=ReportListResponse)
def list_reports(
    case_id: uuid.UUID,
    session: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ReportListResponse:
    reports, total = report_service.list(session, case_id, limit=limit, offset=offset)
    return ReportListResponse(
        data=[ReportRead.model_validate(report) for report in reports],
        meta=PaginationMeta(limit=limit, offset=offset, total=total),
    )


@report_router.get("/{report_id}", response_model=ReportRead)
def get_report(report_id: uuid.UUID, session: DatabaseSession) -> ReportRead:
    return ReportRead.model_validate(report_service.get(session, report_id))


@report_router.get("/{report_id}/download", response_class=FileResponse)
def download_report(report_id: uuid.UUID, session: DatabaseSession) -> FileResponse:
    artifact, path = report_service.download(session, report_id)
    media_types = {
        ReportFormat.JSON: "application/json",
        ReportFormat.HTML: "text/html; charset=utf-8",
        ReportFormat.PDF: "application/pdf",
    }
    return FileResponse(
        path,
        media_type=media_types[artifact.format],
        filename=f"report-{report_id}.{artifact.format.value}",
    )
