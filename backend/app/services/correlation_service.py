from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import ConflictError, InfrastructureError, NotFoundError
from app.correlation.registry import correlation_rule_registry
from app.correlation.rules import (
    DEFAULT_TEMPORAL_WINDOW_SECONDS,
    RULE_SET_VERSION,
    CorrelationCandidate,
)
from app.db.models import (
    AuditEvent,
    Case,
    CorrelationMatch,
    CorrelationMatchEvent,
    CorrelationRun,
    Finding,
    TimelineEvent,
)
from app.domain.enums import (
    CorrelationRunStatus,
    FindingConfidence,
    FindingSeverity,
    FindingStatus,
)
from app.schemas.correlation import FindingUpdate
from app.services.case_service import LOCAL_AUDIT_ACTOR

logger = logging.getLogger(__name__)

VALID_FINDING_TRANSITIONS = {
    FindingStatus.OPEN: {FindingStatus.REVIEWED, FindingStatus.DISMISSED},
    FindingStatus.REVIEWED: {FindingStatus.RESOLVED, FindingStatus.DISMISSED},
    FindingStatus.RESOLVED: set(),
    FindingStatus.DISMISSED: set(),
}


class CorrelationService:
    def run(
        self,
        session: Session,
        case_id: uuid.UUID,
        *,
        temporal_window_seconds: int = DEFAULT_TEMPORAL_WINDOW_SECONDS,
    ) -> CorrelationRun:
        case = session.scalar(select(Case).where(Case.id == case_id).with_for_update())
        if case is None:
            raise NotFoundError("Case was not found")
        events = tuple(
            session.scalars(
                select(TimelineEvent)
                .where(TimelineEvent.case_id == case_id)
                .order_by(
                    TimelineEvent.event_time.asc().nulls_last(),
                    TimelineEvent.source_identifier.asc().nulls_last(),
                    TimelineEvent.time_source.asc(),
                    TimelineEvent.event_ordinal.asc(),
                    TimelineEvent.id.asc(),
                )
                .execution_options(yield_per=1000)
            )
        )
        rules = correlation_rule_registry.rules()
        warnings: list[str] = []
        candidates: list[CorrelationCandidate] = []
        for rule in rules:
            result = rule.evaluate(events, temporal_window_seconds)
            candidates.extend(result.candidates)
            warnings.extend(result.warnings)
        candidates.sort(key=_candidate_sort_key)
        now = datetime.now(UTC)
        run = CorrelationRun(
            case_id=case_id,
            started_at=now,
            completed_at=None,
            status=CorrelationRunStatus.RUNNING,
            rule_set_version=RULE_SET_VERSION,
            temporal_window_seconds=temporal_window_seconds,
            event_count=len(events),
            matched_count=0,
            finding_count=0,
            rules_evaluated=[
                {"rule_id": rule.rule_id, "rule_version": rule.version, "name": rule.name}
                for rule in rules
            ],
            warnings=warnings,
            errors=[],
        )
        try:
            session.add(run)
            session.flush()
            matches_created = 0
            findings_created = 0
            for candidate in candidates:
                match_key = _match_key(case_id, candidate)
                existing = session.scalar(
                    select(CorrelationMatch).where(CorrelationMatch.deterministic_key == match_key)
                )
                if existing is not None:
                    continue
                match = CorrelationMatch(
                    correlation_run_id=run.id,
                    case_id=case_id,
                    rule_id=candidate.rule_id,
                    rule_version=candidate.rule_version,
                    deterministic_key=match_key,
                    temporal_delta_seconds=candidate.temporal_delta_seconds,
                    match_basis=candidate.match_basis,
                    explanation=candidate.explanation,
                    metadata_={
                        "matched_fields": list(candidate.matched_fields),
                        "normalized_identity": candidate.normalized_identity,
                        "temporal_window_seconds": temporal_window_seconds,
                        "temporal_delta_seconds": candidate.temporal_delta_seconds,
                        "signed_delta_seconds": candidate.signed_delta_seconds,
                        "event_a_time": candidate.event_a.event_time.isoformat()
                        if candidate.event_a.event_time
                        else None,
                        "event_b_time": candidate.event_b.event_time.isoformat()
                        if candidate.event_b.event_time
                        else None,
                    },
                )
                session.add(match)
                session.flush()
                session.add_all(
                    [
                        CorrelationMatchEvent(
                            correlation_match_id=match.id,
                            timeline_event_id=candidate.event_a.id,
                            event_role=candidate.event_a_role,
                            event_order=0,
                        ),
                        CorrelationMatchEvent(
                            correlation_match_id=match.id,
                            timeline_event_id=candidate.event_b.id,
                            event_role=candidate.event_b_role,
                            event_order=1,
                        ),
                    ]
                )
                finding_key = hashlib.sha256(f"finding|{match_key}".encode()).hexdigest()
                finding = Finding(
                    case_id=case_id,
                    correlation_run_id=run.id,
                    correlation_match_id=match.id,
                    finding_type=candidate.finding_type,
                    title=candidate.finding_title,
                    description=candidate.finding_description,
                    status=FindingStatus.OPEN,
                    severity=candidate.severity,
                    confidence=candidate.confidence,
                    rule_id=candidate.rule_id,
                    rule_version=candidate.rule_version,
                    deterministic_key=finding_key,
                    metadata_={
                        "match_basis": candidate.match_basis,
                        "requires_examiner_review": True,
                    },
                )
                session.add(finding)
                session.flush()
                session.add(
                    AuditEvent(
                        case_id=case_id,
                        evidence_id=None,
                        action="FINDING_CREATED",
                        actor=LOCAL_AUDIT_ACTOR,
                        details={
                            "finding_id": str(finding.id),
                            "correlation_match_id": str(match.id),
                            "rule_id": candidate.rule_id,
                            "rule_version": candidate.rule_version,
                        },
                    )
                )
                matches_created += 1
                findings_created += 1
            completed_at = datetime.now(UTC)
            run.completed_at = completed_at
            run.status = (
                CorrelationRunStatus.COMPLETED_WITH_WARNINGS
                if warnings
                else CorrelationRunStatus.COMPLETED
            )
            run.matched_count = matches_created
            run.finding_count = findings_created
            session.add(
                AuditEvent(
                    case_id=case_id,
                    evidence_id=None,
                    action="CORRELATION_RUN",
                    actor=LOCAL_AUDIT_ACTOR,
                    details={
                        "correlation_run_id": str(run.id),
                        "rule_set_version": RULE_SET_VERSION,
                        "rules": [
                            {"rule_id": rule.rule_id, "rule_version": rule.version}
                            for rule in rules
                        ],
                        "event_count": len(events),
                        "match_count": matches_created,
                        "finding_count": findings_created,
                        "warning_count": len(warnings),
                    },
                )
            )
            session.commit()
            session.refresh(run)
            return run
        except SQLAlchemyError as error:
            session.rollback()
            logger.exception("Correlation run persistence failed")
            raise InfrastructureError("Correlation run persistence failed") from error

    def list_matches(
        self,
        session: Session,
        case_id: uuid.UUID,
        *,
        rule_id: str | None,
        correlation_run_id: uuid.UUID | None,
        limit: int,
        offset: int,
    ) -> tuple[list[CorrelationMatch], int]:
        self._case_exists(session, case_id)
        statement = select(CorrelationMatch).where(CorrelationMatch.case_id == case_id)
        count = (
            select(func.count())
            .select_from(CorrelationMatch)
            .where(CorrelationMatch.case_id == case_id)
        )
        if rule_id is not None:
            statement = statement.where(CorrelationMatch.rule_id == rule_id)
            count = count.where(CorrelationMatch.rule_id == rule_id)
        if correlation_run_id is not None:
            statement = statement.where(CorrelationMatch.correlation_run_id == correlation_run_id)
            count = count.where(CorrelationMatch.correlation_run_id == correlation_run_id)
        matches = list(
            session.scalars(
                statement.options(
                    selectinload(CorrelationMatch.event_links).selectinload(
                        CorrelationMatchEvent.timeline_event
                    )
                )
                .order_by(
                    CorrelationMatch.created_at.desc(),
                    CorrelationMatch.rule_id.asc(),
                    CorrelationMatch.deterministic_key.asc(),
                )
                .limit(limit)
                .offset(offset)
            )
        )
        return matches, session.scalar(count) or 0

    def list_findings(
        self,
        session: Session,
        case_id: uuid.UUID,
        *,
        status: FindingStatus | None,
        severity: FindingSeverity | None,
        confidence: FindingConfidence | None,
        rule_id: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Finding], int]:
        self._case_exists(session, case_id)
        statement = select(Finding).where(Finding.case_id == case_id)
        count = select(func.count()).select_from(Finding).where(Finding.case_id == case_id)
        for column, value in (
            (Finding.status, status),
            (Finding.severity, severity),
            (Finding.confidence, confidence),
            (Finding.rule_id, rule_id),
        ):
            if value is not None:
                statement = statement.where(column == value)
                count = count.where(column == value)
        findings = list(
            session.scalars(
                statement.options(
                    selectinload(Finding.correlation_match)
                    .selectinload(CorrelationMatch.event_links)
                    .selectinload(CorrelationMatchEvent.timeline_event)
                )
                .order_by(Finding.created_at.desc(), Finding.deterministic_key.asc())
                .limit(limit)
                .offset(offset)
            )
        )
        return findings, session.scalar(count) or 0

    def get_finding(self, session: Session, finding_id: uuid.UUID) -> Finding:
        finding = session.scalar(
            select(Finding)
            .options(
                selectinload(Finding.correlation_match)
                .selectinload(CorrelationMatch.event_links)
                .selectinload(CorrelationMatchEvent.timeline_event)
            )
            .where(Finding.id == finding_id)
        )
        if finding is None:
            raise NotFoundError("Finding was not found")
        return finding

    def update_finding(
        self, session: Session, finding_id: uuid.UUID, payload: FindingUpdate
    ) -> Finding:
        finding = session.scalar(select(Finding).where(Finding.id == finding_id).with_for_update())
        if finding is None:
            raise NotFoundError("Finding was not found")
        old_status = finding.status
        if payload.status is not None and payload.status != finding.status:
            if payload.status not in VALID_FINDING_TRANSITIONS[finding.status]:
                raise ConflictError(
                    f"Finding cannot transition from {finding.status.value} "
                    f"to {payload.status.value}"
                )
            finding.status = payload.status
        if payload.severity is not None:
            finding.severity = payload.severity
        if payload.confidence is not None:
            finding.confidence = payload.confidence
        if "analyst_notes" in payload.model_fields_set:
            finding.analyst_notes = payload.analyst_notes
        details: dict[str, object] = {
            "finding_id": str(finding.id),
            "updated_fields": sorted(payload.model_fields_set),
        }
        try:
            session.add(
                AuditEvent(
                    case_id=finding.case_id,
                    evidence_id=None,
                    action="FINDING_UPDATED",
                    actor=LOCAL_AUDIT_ACTOR,
                    details=details,
                )
            )
            if finding.status != old_status:
                session.add(
                    AuditEvent(
                        case_id=finding.case_id,
                        evidence_id=None,
                        action="FINDING_STATUS_CHANGED",
                        actor=LOCAL_AUDIT_ACTOR,
                        details={
                            "finding_id": str(finding.id),
                            "from": old_status.value,
                            "to": finding.status.value,
                        },
                    )
                )
            session.commit()
            return self.get_finding(session, finding.id)
        except SQLAlchemyError as error:
            session.rollback()
            logger.exception("Finding update persistence failed")
            raise InfrastructureError("Finding update persistence failed") from error

    @staticmethod
    def _case_exists(session: Session, case_id: uuid.UUID) -> None:
        if session.get(Case, case_id) is None:
            raise NotFoundError("Case was not found")


def _match_key(case_id: uuid.UUID, candidate: CorrelationCandidate) -> str:
    event_ids = sorted((str(candidate.event_a.id), str(candidate.event_b.id)))
    value = "|".join(
        (
            str(case_id),
            candidate.rule_id,
            candidate.rule_version,
            *event_ids,
            candidate.match_basis,
            candidate.normalized_identity,
        )
    )
    return hashlib.sha256(value.encode()).hexdigest()


def _candidate_sort_key(candidate: CorrelationCandidate) -> tuple[object, ...]:
    return (
        candidate.rule_id,
        candidate.event_a.event_time,
        candidate.event_b.event_time,
        candidate.event_a.source_identifier or "",
        candidate.event_b.source_identifier or "",
        candidate.normalized_identity,
        str(candidate.event_a.id),
        str(candidate.event_b.id),
    )


correlation_service = CorrelationService()
