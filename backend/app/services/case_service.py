import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import Sequence, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, InfrastructureError, NotFoundError
from app.db.models import AuditEvent, Case
from app.domain.enums import CaseStatus
from app.schemas.case import CaseCreate, CaseUpdate

CASE_NUMBER_SEQUENCE = Sequence("case_number_seq")
LOCAL_AUDIT_ACTOR = "LOCAL_APPLICATION"


class CaseService:
    def create(self, session: Session, payload: CaseCreate) -> Case:
        try:
            sequence_value = session.scalar(CASE_NUMBER_SEQUENCE.next_value())
            if sequence_value is None:
                raise InfrastructureError("Case number sequence returned no value")
            case = Case(
                case_number=f"CASE-{datetime.now(UTC).year}-{sequence_value:04d}",
                name=payload.name,
                description=payload.description,
                investigator=payload.investigator,
                status=CaseStatus.OPEN,
            )
            session.add(case)
            session.flush()
            session.add(
                AuditEvent(
                    case_id=case.id,
                    action="CASE_CREATED",
                    actor=LOCAL_AUDIT_ACTOR,
                    details={"case_number": case.case_number, "status": CaseStatus.OPEN.value},
                )
            )
            session.commit()
            session.refresh(case)
            return case
        except SQLAlchemyError as error:
            session.rollback()
            raise InfrastructureError("Case creation failed") from error

    def list(self, session: Session, *, limit: int, offset: int) -> tuple[list[Case], int]:
        cases = list(
            session.scalars(
                select(Case)
                .order_by(Case.created_at.desc(), Case.case_number.desc(), Case.id.desc())
                .limit(limit)
                .offset(offset)
            )
        )
        total = session.scalar(select(func.count()).select_from(Case)) or 0
        return cases, total

    def get(self, session: Session, case_id: uuid.UUID) -> Case:
        case = session.get(Case, case_id)
        if case is None:
            raise NotFoundError("Case was not found")
        return case

    def update(self, session: Session, case_id: uuid.UUID, payload: CaseUpdate) -> Case:
        case = self._get_for_update(session, case_id)
        changes = payload.model_dump(exclude_unset=True)
        try:
            for field, value in changes.items():
                setattr(case, field, value)
            case.updated_at = self._next_updated_at(case.updated_at)
            session.add(
                AuditEvent(
                    case_id=case.id,
                    action="CASE_UPDATED",
                    actor=LOCAL_AUDIT_ACTOR,
                    details={"fields": sorted(changes)},
                )
            )
            session.commit()
            session.refresh(case)
            return case
        except SQLAlchemyError as error:
            session.rollback()
            raise InfrastructureError("Case update failed") from error

    def close(self, session: Session, case_id: uuid.UUID) -> Case:
        return self._transition(
            session,
            case_id,
            expected=CaseStatus.OPEN,
            target=CaseStatus.CLOSED,
            action="CASE_CLOSED",
        )

    def archive(self, session: Session, case_id: uuid.UUID) -> Case:
        return self._transition(
            session,
            case_id,
            expected=CaseStatus.CLOSED,
            target=CaseStatus.ARCHIVED,
            action="CASE_ARCHIVED",
        )

    def _get_for_update(self, session: Session, case_id: uuid.UUID) -> Case:
        case = session.scalar(select(Case).where(Case.id == case_id).with_for_update())
        if case is None:
            raise NotFoundError("Case was not found")
        return case

    def _transition(
        self,
        session: Session,
        case_id: uuid.UUID,
        *,
        expected: CaseStatus,
        target: CaseStatus,
        action: str,
    ) -> Case:
        case = self._get_for_update(session, case_id)
        if case.status is not expected:
            session.rollback()
            raise ConflictError(
                f"Case cannot transition from {case.status.value} to {target.value}"
            )
        try:
            previous_status = case.status
            case.status = target
            case.updated_at = self._next_updated_at(case.updated_at)
            session.add(
                AuditEvent(
                    case_id=case.id,
                    action=action,
                    actor=LOCAL_AUDIT_ACTOR,
                    details={"from": previous_status.value, "to": target.value},
                )
            )
            session.commit()
            session.refresh(case)
            return case
        except SQLAlchemyError as error:
            session.rollback()
            raise InfrastructureError("Case lifecycle transition failed") from error

    @staticmethod
    def _next_updated_at(current: datetime) -> datetime:
        now = datetime.now(UTC)
        return now if now > current else current + timedelta(microseconds=1)


case_service = CaseService()
