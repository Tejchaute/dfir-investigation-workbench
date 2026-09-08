import uuid
from datetime import UTC, datetime
from typing import BinaryIO

from sqlalchemy import Sequence, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import ConflictError, InfrastructureError, NotFoundError
from app.db.models import AuditEvent, Case, ChainOfCustodyEntry, Evidence, EvidenceHash
from app.domain.enums import CaseStatus
from app.schemas.evidence import EvidenceRegistration, EvidenceVerificationRead
from app.services.case_service import LOCAL_AUDIT_ACTOR
from app.services.evidence_storage import EvidenceStorage, StoredEvidence

EVIDENCE_NUMBER_SEQUENCE = Sequence("evidence_number_seq")


class EvidenceService:
    def __init__(self, storage: EvidenceStorage | None = None) -> None:
        self.storage = storage or EvidenceStorage(get_settings().evidence_root)

    def register(
        self,
        session: Session,
        case_id: uuid.UUID,
        filename: str | None,
        source: BinaryIO,
        payload: EvidenceRegistration,
    ) -> Evidence:
        safe_filename = self.storage.validate_filename(filename)
        case = session.scalar(select(Case).where(Case.id == case_id).with_for_update())
        if case is None:
            raise NotFoundError("Case was not found")
        if case.status is not CaseStatus.OPEN:
            session.rollback()
            raise ConflictError("Evidence can only be registered to an open case")

        evidence_id = uuid.uuid4()
        stored: StoredEvidence | None = None
        try:
            sequence_value = session.scalar(EVIDENCE_NUMBER_SEQUENCE.next_value())
            if sequence_value is None:
                raise InfrastructureError("Evidence number sequence returned no value")
            stored = self.storage.store(source, case_id, evidence_id)
            now = datetime.now(UTC)
            evidence = Evidence(
                id=evidence_id,
                case_id=case_id,
                evidence_number=f"EVD-{now.year}-{sequence_value:04d}",
                name=safe_filename,
                description=payload.description,
                evidence_type=payload.evidence_type,
                original_path=None,
                stored_path=stored.relative_path,
                size_bytes=stored.size_bytes,
                collected_by=payload.collected_by,
                collected_at=payload.collected_at,
            )
            session.add(evidence)
            session.flush()
            session.add_all(
                [
                    EvidenceHash(
                        evidence_id=evidence.id,
                        algorithm="SHA256",
                        digest=stored.digest,
                        computed_at=now,
                        purpose="ACQUISITION",
                    ),
                    ChainOfCustodyEntry(
                        evidence_id=evidence.id,
                        timestamp=now,
                        person=payload.custody_person,
                        action="REGISTERED",
                        location=payload.custody_location,
                        notes=payload.custody_notes,
                    ),
                    AuditEvent(
                        case_id=case_id,
                        evidence_id=evidence.id,
                        action="EVIDENCE_REGISTERED",
                        actor=LOCAL_AUDIT_ACTOR,
                        details={
                            "evidence_number": evidence.evidence_number,
                            "algorithm": "SHA256",
                            "size_bytes": stored.size_bytes,
                        },
                    ),
                ]
            )
            session.flush()
            session.refresh(evidence)
            session.commit()
            return evidence
        except SQLAlchemyError as error:
            session.rollback()
            if stored is not None:
                self.storage.cleanup(stored)
            raise InfrastructureError("Evidence registration failed") from error
        except Exception:
            session.rollback()
            if stored is not None:
                self.storage.cleanup(stored)
            raise

    def list_for_case(
        self, session: Session, case_id: uuid.UUID, *, limit: int, offset: int
    ) -> tuple[list[Evidence], int]:
        if session.get(Case, case_id) is None:
            raise NotFoundError("Case was not found")
        items = list(
            session.scalars(
                select(Evidence)
                .where(Evidence.case_id == case_id)
                .order_by(
                    Evidence.created_at.desc(),
                    Evidence.evidence_number.desc(),
                    Evidence.id.desc(),
                )
                .limit(limit)
                .offset(offset)
            )
        )
        total = (
            session.scalar(
                select(func.count()).select_from(Evidence).where(Evidence.case_id == case_id)
            )
            or 0
        )
        return items, total

    def get(self, session: Session, evidence_id: uuid.UUID) -> Evidence:
        evidence = session.get(Evidence, evidence_id)
        if evidence is None:
            raise NotFoundError("Evidence was not found")
        return evidence

    def hashes(self, session: Session, evidence_id: uuid.UUID) -> list[EvidenceHash]:
        self.get(session, evidence_id)
        return list(
            session.scalars(
                select(EvidenceHash)
                .where(EvidenceHash.evidence_id == evidence_id)
                .order_by(EvidenceHash.computed_at.asc(), EvidenceHash.id.asc())
            )
        )

    def custody(self, session: Session, evidence_id: uuid.UUID) -> list[ChainOfCustodyEntry]:
        self.get(session, evidence_id)
        return list(
            session.scalars(
                select(ChainOfCustodyEntry)
                .where(ChainOfCustodyEntry.evidence_id == evidence_id)
                .order_by(ChainOfCustodyEntry.timestamp.asc(), ChainOfCustodyEntry.id.asc())
            )
        )

    def verify(self, session: Session, evidence_id: uuid.UUID) -> EvidenceVerificationRead:
        evidence = self.get(session, evidence_id)
        acquisition = session.scalar(
            select(EvidenceHash)
            .where(
                EvidenceHash.evidence_id == evidence_id,
                EvidenceHash.algorithm == "SHA256",
                EvidenceHash.purpose == "ACQUISITION",
            )
            .order_by(EvidenceHash.computed_at.asc(), EvidenceHash.id.asc())
            .limit(1)
        )
        if acquisition is None or evidence.stored_path is None:
            raise ConflictError("Evidence has no acquisition SHA-256 record")
        recorded_digest = acquisition.digest
        path = self.storage.resolve_for_read(evidence.stored_path)
        calculated_digest, size_bytes = self.storage.calculate_sha256(path)
        verified_at = datetime.now(UTC)
        matches = calculated_digest == recorded_digest
        try:
            session.add_all(
                [
                    EvidenceHash(
                        evidence_id=evidence.id,
                        algorithm="SHA256",
                        digest=calculated_digest,
                        computed_at=verified_at,
                        purpose="VERIFICATION",
                    ),
                    AuditEvent(
                        case_id=evidence.case_id,
                        evidence_id=evidence.id,
                        action="EVIDENCE_VERIFIED",
                        actor=LOCAL_AUDIT_ACTOR,
                        details={"algorithm": "SHA256", "match": matches, "size_bytes": size_bytes},
                    ),
                ]
            )
            session.commit()
        except SQLAlchemyError as error:
            session.rollback()
            raise InfrastructureError("Evidence verification recording failed") from error
        return EvidenceVerificationRead(
            evidence_id=evidence.id,
            algorithm="SHA256",
            recorded_digest=recorded_digest,
            calculated_digest=calculated_digest,
            match=matches,
            verified_at=verified_at,
        )


evidence_service = EvidenceService()
