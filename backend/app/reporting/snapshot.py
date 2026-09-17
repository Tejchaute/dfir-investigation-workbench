from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import NotFoundError
from app.db.models import (
    Artifact,
    AuditEvent,
    Case,
    ChainOfCustodyEntry,
    CorrelationMatch,
    CorrelationRun,
    Evidence,
    Finding,
    TimelineEvent,
)
from app.domain.enums import ReportType
from app.schemas.report import (
    ArtifactReportItem,
    AuditReportItem,
    CaseReportSection,
    CorrelationMatchReportItem,
    CorrelationRunReportItem,
    CustodyReportItem,
    EvidenceReportItem,
    FindingReportItem,
    IntegrityReportItem,
    ReportIdentification,
    ReportSnapshot,
    TimelineReportItem,
)

REPORT_VERSION = "1.0.0"
GENERATOR_IDENTITY = "LOCAL_APPLICATION"
AUDIT_ACTIONS = frozenset(
    {
        "CASE_CREATED",
        "CASE_UPDATED",
        "CASE_CLOSED",
        "CASE_ARCHIVED",
        "EVIDENCE_REGISTERED",
        "EVIDENCE_VERIFIED",
        "TIMELINE_GENERATED",
        "CORRELATION_RUN",
        "FINDING_CREATED",
        "FINDING_UPDATED",
        "FINDING_STATUS_CHANGED",
        "REPORT_GENERATED",
    }
)
MAX_AUDIT_EVENTS = 500


class ReportSnapshotBuilder:
    def build(
        self,
        session: Session,
        *,
        case_id: uuid.UUID,
        report_id: uuid.UUID,
        generated_at: datetime,
    ) -> ReportSnapshot:
        case = session.get(Case, case_id)
        if case is None:
            raise NotFoundError("Case was not found")

        evidence = list(
            session.scalars(
                select(Evidence)
                .options(selectinload(Evidence.hashes), selectinload(Evidence.custody_entries))
                .where(Evidence.case_id == case_id)
                .order_by(Evidence.evidence_number, Evidence.id)
            )
        )
        evidence_ids = [item.id for item in evidence]
        artifacts = (
            list(
                session.scalars(
                    select(Artifact)
                    .options(selectinload(Artifact.records))
                    .where(Artifact.evidence_id.in_(evidence_ids))
                    .order_by(
                        Artifact.evidence_id,
                        Artifact.artifact_type,
                        Artifact.created_at,
                        Artifact.id,
                    )
                )
            )
            if evidence_ids
            else []
        )
        timeline = list(
            session.scalars(
                select(TimelineEvent)
                .where(TimelineEvent.case_id == case_id)
                .order_by(
                    TimelineEvent.event_time.asc().nulls_last(),
                    TimelineEvent.artifact_id,
                    TimelineEvent.artifact_record_id,
                    TimelineEvent.event_type,
                    TimelineEvent.event_ordinal,
                    TimelineEvent.id,
                )
            )
        )
        runs = list(
            session.scalars(
                select(CorrelationRun)
                .options(
                    selectinload(CorrelationRun.matches).selectinload(CorrelationMatch.event_links)
                )
                .where(CorrelationRun.case_id == case_id)
                .order_by(CorrelationRun.started_at, CorrelationRun.id)
            )
        )
        findings = list(
            session.scalars(
                select(Finding)
                .options(
                    selectinload(Finding.correlation_match).selectinload(
                        CorrelationMatch.event_links
                    )
                )
                .where(Finding.case_id == case_id)
                .order_by(Finding.created_at, Finding.deterministic_key, Finding.id)
            )
        )
        audits = list(
            session.scalars(
                select(AuditEvent)
                .where(AuditEvent.case_id == case_id, AuditEvent.action.in_(AUDIT_ACTIONS))
                .order_by(AuditEvent.timestamp, AuditEvent.action, AuditEvent.id)
                .limit(MAX_AUDIT_EVENTS)
            )
        )
        evidence_number = {item.id: item.evidence_number for item in evidence}
        closed_at = _audit_timestamp(audits, "CASE_CLOSED")
        archived_at = _audit_timestamp(audits, "CASE_ARCHIVED")

        return ReportSnapshot(
            report_identification=ReportIdentification(
                report_id=report_id,
                report_type=ReportType.FORENSIC_INVESTIGATION_REPORT,
                report_version=REPORT_VERSION,
                generated_at=generated_at,
                generated_by=GENERATOR_IDENTITY,
                case_number=case.case_number,
            ),
            case_information=CaseReportSection(
                case_id=case.id,
                case_number=case.case_number,
                status=case.status.value,
                name=case.name,
                description=case.description,
                investigator=case.investigator,
                created_at=case.created_at,
                updated_at=case.updated_at,
                closed_at=closed_at,
                archived_at=archived_at,
                timestamp_note=(
                    "Timezone offsets are preserved where established; unknown timezone "
                    "semantics are not invented."
                ),
            ),
            evidence_inventory=tuple(_evidence_item(item) for item in evidence),
            evidence_integrity=tuple(_integrity_item(item) for item in evidence),
            chain_of_custody=tuple(
                _custody_item(entry, item.evidence_number)
                for item in evidence
                for entry in sorted(item.custody_entries, key=lambda row: (row.timestamp, row.id))
            ),
            artifact_summary=tuple(
                ArtifactReportItem(
                    artifact_id=item.id,
                    evidence_id=item.evidence_id,
                    evidence_number=evidence_number[item.evidence_id],
                    artifact_type=item.artifact_type.value,
                    parser_name=item.parser_name,
                    parser_version=item.parser_version,
                    status=item.status.value,
                    record_count=len(item.records),
                    created_at=item.created_at,
                )
                for item in artifacts
            ),
            timeline_reconstruction=tuple(_timeline_item(item) for item in timeline),
            correlation_analysis=tuple(_run_item(item) for item in runs),
            findings=tuple(_finding_item(item) for item in findings),
            methodology=_methodology(artifacts, runs),
            limitations=_limitations(timeline, runs),
            audit_summary=tuple(_audit_item(item) for item in audits),
        )


def _evidence_item(item: Evidence) -> EvidenceReportItem:
    return EvidenceReportItem(
        evidence_id=item.id,
        evidence_number=item.evidence_number,
        original_filename=item.name,
        evidence_type=item.evidence_type.value,
        description=item.description,
        size_bytes=item.size_bytes,
        collected_by=item.collected_by,
        collected_at=item.collected_at,
        registration_timestamp=item.created_at,
        acquisition_method=None,
    )


def _integrity_item(item: Evidence) -> IntegrityReportItem:
    ordered = sorted(item.hashes, key=lambda row: (row.computed_at, row.id))
    acquisition = next((row for row in ordered if row.purpose == "ACQUISITION"), None)
    verifications = [row for row in ordered if row.purpose == "VERIFICATION"]
    verification = verifications[-1] if verifications else None
    if acquisition is None:
        status = "ACQUISITION_HASH_UNAVAILABLE"
    elif verification is None:
        status = "NOT_VERIFIED"
    elif (
        acquisition.algorithm == verification.algorithm
        and acquisition.digest == verification.digest
    ):
        status = "MATCH"
    else:
        status = "MISMATCH"
    return IntegrityReportItem(
        evidence_id=item.id,
        evidence_number=item.evidence_number,
        algorithm=acquisition.algorithm
        if acquisition
        else verification.algorithm
        if verification
        else None,
        acquisition_digest=acquisition.digest if acquisition else None,
        acquisition_computed_at=acquisition.computed_at if acquisition else None,
        verification_digest=verification.digest if verification else None,
        last_verified_at=verification.computed_at if verification else None,
        verification_status=status,
    )


def _custody_item(entry: ChainOfCustodyEntry, number: str) -> CustodyReportItem:
    return CustodyReportItem(
        entry_id=entry.id,
        evidence_id=entry.evidence_id,
        evidence_number=number,
        timestamp=entry.timestamp,
        person=entry.person,
        action=entry.action,
        location=entry.location,
        notes=entry.notes,
    )


def _timeline_item(item: TimelineEvent) -> TimelineReportItem:
    return TimelineReportItem(
        event_id=item.id,
        evidence_id=item.evidence_id,
        artifact_id=item.artifact_id,
        artifact_record_id=item.artifact_record_id,
        event_time=item.event_time,
        raw_time=item.raw_time,
        event_type=item.event_type.value,
        artifact_type=item.artifact_type.value,
        time_source=item.time_source,
        time_semantics=item.time_semantics,
        timestamp_precision=item.timestamp_precision.value,
        source_identifier=item.source_identifier,
        description=item.description,
        metadata=item.metadata_,
        provenance=item.provenance,
    )


def _run_item(run: CorrelationRun) -> CorrelationRunReportItem:
    matches = sorted(run.matches, key=lambda row: (row.rule_id, row.deterministic_key, row.id))
    return CorrelationRunReportItem(
        run_id=run.id,
        started_at=run.started_at,
        completed_at=run.completed_at,
        status=run.status.value,
        rule_set_version=run.rule_set_version,
        temporal_window_seconds=run.temporal_window_seconds,
        match_count=run.matched_count,
        finding_count=run.finding_count,
        matches=tuple(
            CorrelationMatchReportItem(
                match_id=match.id,
                run_id=run.id,
                rule_id=match.rule_id,
                rule_version=match.rule_version,
                match_basis=match.match_basis,
                temporal_delta_seconds=match.temporal_delta_seconds,
                explanation=match.explanation,
                timeline_event_ids=tuple(
                    link.timeline_event_id
                    for link in sorted(match.event_links, key=lambda row: row.event_order)
                ),
                metadata=match.metadata_,
            )
            for match in matches
        ),
    )


def _finding_item(item: Finding) -> FindingReportItem:
    links = sorted(item.correlation_match.event_links, key=lambda row: row.event_order)
    return FindingReportItem(
        finding_id=item.id,
        correlation_match_id=item.correlation_match_id,
        finding_type=item.finding_type.value,
        title=item.title,
        description=item.description,
        status=item.status.value,
        severity=item.severity.value,
        confidence=item.confidence.value,
        rule_id=item.rule_id,
        rule_version=item.rule_version,
        analyst_notes=item.analyst_notes,
        created_at=item.created_at,
        updated_at=item.updated_at,
        timeline_event_ids=tuple(link.timeline_event_id for link in links),
        provenance={
            "correlation_match_id": str(item.correlation_match_id),
            "timeline_event_ids": [str(link.timeline_event_id) for link in links],
        },
    )


def _methodology(artifacts: list[Artifact], runs: list[CorrelationRun]) -> tuple[str, ...]:
    entries = [
        "Evidence metadata and SHA-256 integrity values were obtained from the controlled "
        "evidence workflow.",
        "Chain-of-custody entries were reproduced chronologically without modification.",
    ]
    for parser_name, parser_version, artifact_type in sorted(
        {(row.parser_name, row.parser_version, row.artifact_type.value) for row in artifacts}
    ):
        entries.append(
            f"{artifact_type} observations were produced by parser {parser_name} "
            f"version {parser_version}."
        )
    if artifacts:
        entries.append(
            "Persisted ArtifactRecords were normalized by the Timeline Engine; evidence was "
            "not reparsed for this report."
        )
    for rule_id, version in sorted(
        {
            (str(rule["rule_id"]), str(rule["rule_version"]))
            for run in runs
            for rule in run.rules_evaluated
            if "rule_id" in rule and "rule_version" in rule
        }
    ):
        entries.append(f"Correlation rule {rule_id} version {version} was recorded as evaluated.")
    entries.append(f"This export was rendered by DFIR_REPORT {REPORT_VERSION}.")
    return tuple(entries)


def _limitations(timeline: list[TimelineEvent], runs: list[CorrelationRun]) -> tuple[str, ...]:
    limits = [
        "Correlation is deterministic and does not establish causality.",
        "The system does not automatically determine maliciousness or user intent.",
        "Findings are analytical relationships requiring examiner review.",
        "Absence of a finding does not establish absence of activity.",
    ]
    if any(item.event_time is None for item in timeline):
        limits.append(
            "One or more source timestamps could not be normalized without inventing timezone "
            "semantics."
        )
    if any(match.match_basis == "basename_match" for run in runs for match in run.matches):
        limits.append("Basename matches are less specific than exact full-path matches.")
    if any(run.warnings for run in runs):
        limits.append(
            "Correlation runs contain warnings; unsupported relationships were not silently "
            "inferred."
        )
    if any(item.artifact_type.value == "NTFS_MFT" for item in timeline):
        limits.append(
            "NTFS support is focused MFT metadata analysis, not complete NTFS reconstruction."
        )
    return tuple(limits)


def _audit_timestamp(audits: list[AuditEvent], action: str) -> datetime | None:
    return next((item.timestamp for item in reversed(audits) if item.action == action), None)


def _audit_item(item: AuditEvent) -> AuditReportItem:
    return AuditReportItem(
        audit_event_id=item.id,
        evidence_id=item.evidence_id,
        action=item.action,
        actor=item.actor,
        timestamp=item.timestamp,
        details=_bounded_details(item.details),
    )


def _bounded_details(details: dict[str, object] | None) -> dict[str, object] | None:
    if details is None:
        return None
    allowed = sorted(details)[:25]
    return {key: details[key] for key in allowed}


report_snapshot_builder = ReportSnapshotBuilder()
