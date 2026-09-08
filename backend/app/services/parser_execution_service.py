import logging
import uuid

from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import func, nullslast, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import ConflictError, InfrastructureError, NotFoundError
from app.db.models import Artifact, ArtifactRecord, AuditEvent, Evidence, EvidenceHash
from app.domain.enums import ArtifactType, ParserExecutionStatus
from app.forensic.parser import ParserContext, ParserResult
from app.forensic.registry import ParserRegistry, parser_registry
from app.services.case_service import LOCAL_AUDIT_ACTOR
from app.services.evidence_storage import EvidenceStorage

logger = logging.getLogger(__name__)


class ParserExecutionService:
    def __init__(
        self,
        registry: ParserRegistry | None = None,
        storage: EvidenceStorage | None = None,
    ) -> None:
        self.registry = registry or parser_registry
        self.storage = storage or EvidenceStorage(get_settings().evidence_root)

    def execute(
        self, session: Session, evidence_id: uuid.UUID, artifact_type: ArtifactType
    ) -> tuple[Artifact, int]:
        evidence = self._eligible_evidence(session, evidence_id)
        parser = self.registry.get(artifact_type)
        if evidence.stored_path is None:
            raise ConflictError("Evidence has no controlled storage reference")
        source_path = self.storage.resolve_for_read(evidence.stored_path)
        try:
            with source_path.open("rb") as source:
                context = ParserContext(
                    evidence_id=evidence.id,
                    case_id=evidence.case_id,
                    evidence_type=evidence.evidence_type,
                    source=source,
                )
                raw_result = parser.parse(context)
            if not isinstance(raw_result, ParserResult):
                raise TypeError("parser returned an invalid result type")
            result = ParserResult.model_validate(raw_result.model_dump())
        except (PydanticValidationError, TypeError) as error:
            logger.warning(
                "Parser %s returned an invalid result: %s", parser.name, type(error).__name__
            )
            result = ParserResult(
                status=ParserExecutionStatus.FAILED,
                errors=("Parser returned an invalid result",),
            )
        except Exception as error:
            logger.exception("Parser %s raised an exception", parser.name)
            result = ParserResult(
                status=ParserExecutionStatus.FAILED,
                errors=(f"Parser execution raised {type(error).__name__}",),
            )
        return self._persist_result(
            session, evidence, artifact_type, parser.name, parser.version, result
        )

    def list_for_evidence(
        self, session: Session, evidence_id: uuid.UUID, *, limit: int, offset: int
    ) -> tuple[list[tuple[Artifact, int]], int]:
        if session.get(Evidence, evidence_id) is None:
            raise NotFoundError("Evidence was not found")
        record_count = (
            select(func.count(ArtifactRecord.id))
            .where(ArtifactRecord.artifact_id == Artifact.id)
            .correlate(Artifact)
            .scalar_subquery()
        )
        rows = list(
            session.execute(
                select(Artifact, record_count)
                .where(Artifact.evidence_id == evidence_id)
                .order_by(Artifact.created_at.desc(), Artifact.id.desc())
                .limit(limit)
                .offset(offset)
            ).tuples()
        )
        total = (
            session.scalar(
                select(func.count())
                .select_from(Artifact)
                .where(Artifact.evidence_id == evidence_id)
            )
            or 0
        )
        return rows, total

    def get(self, session: Session, artifact_id: uuid.UUID) -> tuple[Artifact, int]:
        artifact = session.get(Artifact, artifact_id)
        if artifact is None:
            raise NotFoundError("Artifact was not found")
        count = (
            session.scalar(
                select(func.count())
                .select_from(ArtifactRecord)
                .where(ArtifactRecord.artifact_id == artifact_id)
            )
            or 0
        )
        return artifact, count

    def records(
        self, session: Session, artifact_id: uuid.UUID, *, limit: int, offset: int
    ) -> tuple[list[ArtifactRecord], int]:
        if session.get(Artifact, artifact_id) is None:
            raise NotFoundError("Artifact was not found")
        records = list(
            session.scalars(
                select(ArtifactRecord)
                .where(ArtifactRecord.artifact_id == artifact_id)
                .order_by(
                    nullslast(ArtifactRecord.event_time.asc()),
                    nullslast(ArtifactRecord.source_record_identifier.asc()),
                    ArtifactRecord.id.asc(),
                )
                .limit(limit)
                .offset(offset)
            )
        )
        total = (
            session.scalar(
                select(func.count())
                .select_from(ArtifactRecord)
                .where(ArtifactRecord.artifact_id == artifact_id)
            )
            or 0
        )
        return records, total

    @staticmethod
    def _eligible_evidence(session: Session, evidence_id: uuid.UUID) -> Evidence:
        evidence = session.get(Evidence, evidence_id)
        if evidence is None:
            raise NotFoundError("Evidence was not found")
        acquisition_hash = session.scalar(
            select(EvidenceHash.id).where(
                EvidenceHash.evidence_id == evidence_id,
                EvidenceHash.algorithm == "SHA256",
                EvidenceHash.purpose == "ACQUISITION",
            )
        )
        if acquisition_hash is None:
            raise ConflictError("Evidence is not eligible for parsing without an acquisition hash")
        return evidence

    @staticmethod
    def _persist_result(
        session: Session,
        evidence: Evidence,
        artifact_type: ArtifactType,
        parser_name: str,
        parser_version: str,
        result: ParserResult,
    ) -> tuple[Artifact, int]:
        artifact = Artifact(
            evidence_id=evidence.id,
            artifact_type=artifact_type,
            parser_name=parser_name,
            parser_version=parser_version,
            status=result.status,
            metadata_=result.metadata,
            warnings=list(result.warnings),
            errors=list(result.errors),
            statistics=result.statistics,
        )
        try:
            session.add(artifact)
            session.flush()
            session.add_all(
                [
                    ArtifactRecord(
                        artifact_id=artifact.id,
                        record_type=record.record_type,
                        source_record_identifier=record.source_record_identifier,
                        event_time=record.event_time,
                        data=record.data,
                        provenance=record.provenance,
                    )
                    for record in result.records
                ]
            )
            session.add(
                AuditEvent(
                    case_id=evidence.case_id,
                    evidence_id=evidence.id,
                    action="PARSER_EXECUTED",
                    actor=LOCAL_AUDIT_ACTOR,
                    details={
                        "artifact_id": str(artifact.id),
                        "artifact_type": artifact_type.value,
                        "parser_name": parser_name,
                        "parser_version": parser_version,
                        "status": result.status.value,
                        "record_count": len(result.records),
                        "warning_count": len(result.warnings),
                        "error_count": len(result.errors),
                    },
                )
            )
            session.flush()
            session.refresh(artifact)
            session.commit()
            return artifact, len(result.records)
        except SQLAlchemyError as error:
            session.rollback()
            raise InfrastructureError("Parser execution persistence failed") from error


parser_execution_service = ParserExecutionService()
