from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import TypeVar, cast

from sqlalchemy import Select, Table, func, nullslast, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import InfrastructureError, NotFoundError, ValidationError
from app.db.models import Artifact, ArtifactRecord, AuditEvent, Case, Evidence, TimelineEvent
from app.domain.enums import ArtifactType, TimelineEventType
from app.services.case_service import LOCAL_AUDIT_ACTOR
from app.services.timeline_normalizer import timeline_normalizer

SelectType = TypeVar("SelectType")
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TimelineGenerationStats:
    case_id: uuid.UUID
    artifacts_considered: int
    records_considered: int
    events_created: int
    events_skipped: int
    warnings: list[str]
    unsupported_artifact_types: list[ArtifactType]


class TimelineService:
    def generate(self, session: Session, case_id: uuid.UUID) -> TimelineGenerationStats:
        if session.get(Case, case_id) is None:
            raise NotFoundError("Case was not found")
        artifacts = list(
            session.scalars(
                select(Artifact)
                .join(Evidence, Artifact.evidence_id == Evidence.id)
                .where(Evidence.case_id == case_id)
                .order_by(Artifact.created_at.asc(), Artifact.id.asc())
            )
        )
        artifacts_by_id = {artifact.id: artifact for artifact in artifacts}
        records = list(
            session.scalars(
                select(ArtifactRecord)
                .join(Artifact, ArtifactRecord.artifact_id == Artifact.id)
                .join(Evidence, Artifact.evidence_id == Evidence.id)
                .where(Evidence.case_id == case_id)
                .order_by(ArtifactRecord.artifact_id.asc(), ArtifactRecord.id.asc())
            )
        )
        warnings = [
            f"Artifact {artifact.id}: {warning}"
            for artifact in artifacts
            for warning in artifact.warnings
        ]
        unsupported = sorted(
            {
                artifact.artifact_type
                for artifact in artifacts
                if artifact.artifact_type
                not in {
                    ArtifactType.EVTX,
                    ArtifactType.REGISTRY,
                    ArtifactType.PREFETCH,
                    ArtifactType.LNK,
                    ArtifactType.NTFS_MFT,
                }
            },
            key=lambda item: item.value,
        )
        values: list[dict[str, object]] = []
        records_without_events = 0
        for record in records:
            artifact = artifacts_by_id[record.artifact_id]
            normalized = timeline_normalizer.normalize(artifact, record)
            warnings.extend(
                f"ArtifactRecord {record.id}: {warning}" for warning in normalized.warnings
            )
            if not normalized.events:
                records_without_events += 1
            for event in normalized.events:
                values.append(
                    {
                        "id": uuid.uuid4(),
                        "case_id": case_id,
                        "evidence_id": artifact.evidence_id,
                        "artifact_id": artifact.id,
                        "artifact_record_id": record.id,
                        "parser_name": artifact.parser_name,
                        "parser_version": artifact.parser_version,
                        "artifact_type": artifact.artifact_type,
                        "event_type": event.event_type,
                        "event_time": event.event_time,
                        "raw_time": event.raw_time,
                        "time_source": event.time_source,
                        "time_semantics": event.time_semantics,
                        "timestamp_precision": event.timestamp_precision,
                        "event_ordinal": event.event_ordinal,
                        "description": event.description,
                        "source_identifier": event.source_identifier,
                        "metadata": event.metadata,
                        "provenance": {
                            **event.provenance,
                            "case_id": str(case_id),
                            "evidence_id": str(artifact.evidence_id),
                            "artifact_id": str(artifact.id),
                            "artifact_record_id": str(record.id),
                        },
                    }
                )
        try:
            created = 0
            if values:
                timeline_table = cast(Table, TimelineEvent.__table__)
                statement = (
                    insert(timeline_table)
                    .values(values)
                    .on_conflict_do_nothing(constraint="uq_timeline_events_logical_identity")
                    .returning(timeline_table.c.id)
                )
                created = len(list(session.scalars(statement)))
            skipped = len(values) - created + records_without_events
            session.add(
                AuditEvent(
                    case_id=case_id,
                    evidence_id=None,
                    action="TIMELINE_GENERATED",
                    actor=LOCAL_AUDIT_ACTOR,
                    details={
                        "case_id": str(case_id),
                        "artifacts_considered": len(artifacts),
                        "records_considered": len(records),
                        "events_created": created,
                        "events_skipped": skipped,
                        "warning_count": len(warnings),
                        "unsupported_artifact_types": [item.value for item in unsupported],
                    },
                )
            )
            session.commit()
        except SQLAlchemyError as error:
            session.rollback()
            logger.exception("Timeline generation persistence failed")
            raise InfrastructureError("Timeline generation persistence failed") from error
        return TimelineGenerationStats(
            case_id=case_id,
            artifacts_considered=len(artifacts),
            records_considered=len(records),
            events_created=created,
            events_skipped=skipped,
            warnings=warnings,
            unsupported_artifact_types=unsupported,
        )

    def list_events(
        self,
        session: Session,
        case_id: uuid.UUID,
        *,
        start_time: datetime | None,
        end_time: datetime | None,
        event_type: TimelineEventType | None,
        artifact_type: ArtifactType | None,
        evidence_id: uuid.UUID | None,
        source_identifier: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[TimelineEvent], int]:
        if session.get(Case, case_id) is None:
            raise NotFoundError("Case was not found")
        self._validate_range(start_time, end_time)
        statement = select(TimelineEvent).where(TimelineEvent.case_id == case_id)
        statement = self._filters(
            statement,
            start_time=start_time,
            end_time=end_time,
            event_type=event_type,
            artifact_type=artifact_type,
            evidence_id=evidence_id,
            source_identifier=source_identifier,
        )
        records = list(
            session.scalars(
                statement.order_by(
                    nullslast(TimelineEvent.event_time.asc()),
                    TimelineEvent.artifact_id.asc(),
                    TimelineEvent.artifact_record_id.asc(),
                    TimelineEvent.event_type.asc(),
                    TimelineEvent.event_ordinal.asc(),
                    TimelineEvent.time_source.asc(),
                    TimelineEvent.id.asc(),
                )
                .limit(limit)
                .offset(offset)
            )
        )
        count_statement = (
            select(func.count()).select_from(TimelineEvent).where(TimelineEvent.case_id == case_id)
        )
        count_statement = self._filters(
            count_statement,
            start_time=start_time,
            end_time=end_time,
            event_type=event_type,
            artifact_type=artifact_type,
            evidence_id=evidence_id,
            source_identifier=source_identifier,
        )
        return records, session.scalar(count_statement) or 0

    @staticmethod
    def _filters(
        statement: Select[tuple[SelectType]],
        *,
        start_time: datetime | None,
        end_time: datetime | None,
        event_type: TimelineEventType | None,
        artifact_type: ArtifactType | None,
        evidence_id: uuid.UUID | None,
        source_identifier: str | None,
    ) -> Select[tuple[SelectType]]:
        if start_time is not None:
            statement = statement.where(TimelineEvent.event_time >= start_time)
        if end_time is not None:
            statement = statement.where(TimelineEvent.event_time <= end_time)
        if event_type is not None:
            statement = statement.where(TimelineEvent.event_type == event_type)
        if artifact_type is not None:
            statement = statement.where(TimelineEvent.artifact_type == artifact_type)
        if evidence_id is not None:
            statement = statement.where(TimelineEvent.evidence_id == evidence_id)
        if source_identifier is not None:
            statement = statement.where(TimelineEvent.source_identifier == source_identifier)
        return statement

    @staticmethod
    def _validate_range(start_time: datetime | None, end_time: datetime | None) -> None:
        for value in (start_time, end_time):
            if value is not None and (value.tzinfo is None or value.utcoffset() is None):
                raise ValidationError("Timeline filters must include an explicit timezone")
        if start_time is not None and end_time is not None and start_time > end_time:
            raise ValidationError("start_time must not be after end_time")


timeline_service = TimelineService()
