import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domain.enums import ReportFormat, ReportStatus, ReportType
from app.schemas.case import PaginationMeta
from app.schemas.common import ReadSchema


class FrozenReportModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class ReportIdentification(FrozenReportModel):
    report_id: uuid.UUID
    report_type: ReportType
    report_version: str
    generated_at: datetime
    generated_by: str
    case_number: str


class CaseReportSection(FrozenReportModel):
    case_id: uuid.UUID
    case_number: str
    status: str
    name: str
    description: str | None
    investigator: str | None
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None
    archived_at: datetime | None
    timestamp_note: str


class EvidenceReportItem(FrozenReportModel):
    evidence_id: uuid.UUID
    evidence_number: str
    original_filename: str
    evidence_type: str
    description: str | None
    size_bytes: int | None
    collected_by: str | None
    collected_at: datetime | None
    registration_timestamp: datetime
    acquisition_method: str | None


class IntegrityReportItem(FrozenReportModel):
    evidence_id: uuid.UUID
    evidence_number: str
    algorithm: str | None
    acquisition_digest: str | None
    acquisition_computed_at: datetime | None
    verification_digest: str | None
    last_verified_at: datetime | None
    verification_status: str


class CustodyReportItem(FrozenReportModel):
    entry_id: uuid.UUID
    evidence_id: uuid.UUID
    evidence_number: str
    timestamp: datetime
    person: str
    action: str
    location: str | None
    notes: str | None


class ArtifactReportItem(FrozenReportModel):
    artifact_id: uuid.UUID
    evidence_id: uuid.UUID
    evidence_number: str
    artifact_type: str
    parser_name: str
    parser_version: str
    status: str
    record_count: int
    created_at: datetime


class TimelineReportItem(FrozenReportModel):
    event_id: uuid.UUID
    evidence_id: uuid.UUID
    artifact_id: uuid.UUID
    artifact_record_id: uuid.UUID
    event_time: datetime | None
    raw_time: str | None
    event_type: str
    artifact_type: str
    time_source: str
    time_semantics: str
    timestamp_precision: str
    source_identifier: str | None
    description: str
    metadata: dict[str, object]
    provenance: dict[str, object]


class CorrelationMatchReportItem(FrozenReportModel):
    match_id: uuid.UUID
    run_id: uuid.UUID
    rule_id: str
    rule_version: str
    match_basis: str
    temporal_delta_seconds: float
    explanation: str
    timeline_event_ids: tuple[uuid.UUID, ...]
    metadata: dict[str, object]


class CorrelationRunReportItem(FrozenReportModel):
    run_id: uuid.UUID
    started_at: datetime
    completed_at: datetime | None
    status: str
    rule_set_version: str
    temporal_window_seconds: int
    match_count: int
    finding_count: int
    matches: tuple[CorrelationMatchReportItem, ...]


class FindingReportItem(FrozenReportModel):
    finding_id: uuid.UUID
    correlation_match_id: uuid.UUID
    finding_type: str
    title: str
    description: str
    status: str
    severity: str
    confidence: str
    rule_id: str
    rule_version: str
    analyst_notes: str | None
    created_at: datetime
    updated_at: datetime
    timeline_event_ids: tuple[uuid.UUID, ...]
    provenance: dict[str, object]


class AuditReportItem(FrozenReportModel):
    audit_event_id: uuid.UUID
    evidence_id: uuid.UUID | None
    action: str
    actor: str
    timestamp: datetime
    details: dict[str, object] | None


class ReportSnapshot(FrozenReportModel):
    report_identification: ReportIdentification
    case_information: CaseReportSection
    evidence_inventory: tuple[EvidenceReportItem, ...]
    evidence_integrity: tuple[IntegrityReportItem, ...]
    chain_of_custody: tuple[CustodyReportItem, ...]
    artifact_summary: tuple[ArtifactReportItem, ...]
    timeline_reconstruction: tuple[TimelineReportItem, ...]
    correlation_analysis: tuple[CorrelationRunReportItem, ...]
    findings: tuple[FindingReportItem, ...]
    methodology: tuple[str, ...]
    limitations: tuple[str, ...]
    audit_summary: tuple[AuditReportItem, ...]


class ReportCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    format: ReportFormat
    report_type: ReportType = ReportType.FORENSIC_INVESTIGATION_REPORT


class ReportArtifactRead(ReadSchema):
    id: uuid.UUID
    format: ReportFormat
    content_hash: str
    size_bytes: int
    created_at: datetime


class ReportRead(ReadSchema):
    id: uuid.UUID
    case_id: uuid.UUID
    report_type: ReportType
    report_version: str
    status: ReportStatus
    generated_at: datetime
    generated_by: str
    content_hash: str
    artifacts: list[ReportArtifactRead]
    created_at: datetime


class ReportListResponse(ReadSchema):
    data: list[ReportRead]
    meta: PaginationMeta
