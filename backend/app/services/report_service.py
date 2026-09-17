from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.exceptions import InfrastructureError, NotFoundError
from app.db.models import AuditEvent, Case, Report, ReportArtifact
from app.domain.enums import ReportFormat, ReportStatus, ReportType
from app.reporting.renderers import RENDERERS, canonical_json, sha256_bytes
from app.reporting.snapshot import (
    GENERATOR_IDENTITY,
    REPORT_VERSION,
    report_snapshot_builder,
)
from app.reporting.storage import ReportStorage

logger = logging.getLogger(__name__)


class ReportService:
    def generate(
        self,
        session: Session,
        case_id: uuid.UUID,
        *,
        report_format: ReportFormat,
        report_type: ReportType,
    ) -> Report:
        case = session.scalar(select(Case).where(Case.id == case_id).with_for_update())
        if case is None:
            raise NotFoundError("Case was not found")
        report_id = uuid.uuid4()
        generated_at = datetime.now(UTC)
        settings = get_settings()
        storage = ReportStorage(settings.report_root, settings.evidence_root)
        snapshot_path, output_path = storage.paths(case_id, report_id, report_format.value)
        if report_format == ReportFormat.JSON:
            output_path = snapshot_path
        report = Report(
            id=report_id,
            case_id=case_id,
            report_type=report_type,
            report_version=REPORT_VERSION,
            status=ReportStatus.GENERATED,
            generated_at=generated_at,
            generated_by=GENERATOR_IDENTITY,
            content_hash="0" * 64,
            snapshot_path=storage.relative(snapshot_path),
        )
        written: list[Path] = []
        try:
            session.add(report)
            session.flush()
            audit = AuditEvent(
                case_id=case_id,
                evidence_id=None,
                action="REPORT_GENERATED",
                actor=GENERATOR_IDENTITY,
                timestamp=generated_at,
                details={
                    "report_id": str(report_id),
                    "case_id": str(case_id),
                    "report_type": report_type.value,
                    "report_version": REPORT_VERSION,
                    "format": report_format.value,
                },
            )
            session.add(audit)
            session.flush()
            snapshot = report_snapshot_builder.build(
                session,
                case_id=case_id,
                report_id=report_id,
                generated_at=generated_at,
            )
            snapshot_content = canonical_json(snapshot)
            rendered = RENDERERS[report_format].render(snapshot)
            storage.write_new(snapshot_path, snapshot_content)
            written.append(snapshot_path)
            if output_path != snapshot_path:
                storage.write_new(output_path, rendered)
                written.append(output_path)
            else:
                rendered = snapshot_content
            report.content_hash = sha256_bytes(snapshot_content)
            artifact = ReportArtifact(
                report_id=report.id,
                format=report_format,
                storage_path=storage.relative(output_path),
                content_hash=sha256_bytes(rendered),
                size_bytes=len(rendered),
            )
            session.add(artifact)
            session.commit()
            return self.get(session, report.id)
        except (SQLAlchemyError, OSError, ValueError, InfrastructureError) as error:
            session.rollback()
            storage.cleanup_operation(report_id, tuple(written))
            logger.exception("Report generation failed")
            if isinstance(error, InfrastructureError):
                raise
            raise InfrastructureError("Report generation failed") from error

    def list(
        self, session: Session, case_id: uuid.UUID, *, limit: int, offset: int
    ) -> tuple[list[Report], int]:
        if session.get(Case, case_id) is None:
            raise NotFoundError("Case was not found")
        statement = (
            select(Report)
            .options(selectinload(Report.artifacts))
            .where(Report.case_id == case_id)
            .order_by(Report.generated_at.desc(), Report.id.desc())
            .limit(limit)
            .offset(offset)
        )
        count = select(func.count()).select_from(Report).where(Report.case_id == case_id)
        return list(session.scalars(statement)), session.scalar(count) or 0

    def get(self, session: Session, report_id: uuid.UUID) -> Report:
        report = session.scalar(
            select(Report).options(selectinload(Report.artifacts)).where(Report.id == report_id)
        )
        if report is None:
            raise NotFoundError("Report was not found")
        return report

    def download(self, session: Session, report_id: uuid.UUID) -> tuple[ReportArtifact, Path]:
        report = self.get(session, report_id)
        if len(report.artifacts) != 1:
            raise InfrastructureError("Report artifact metadata is invalid")
        artifact = report.artifacts[0]
        settings = get_settings()
        storage = ReportStorage(settings.report_root, settings.evidence_root)
        path = storage.resolve(artifact.storage_path)
        if sha256_bytes(path.read_bytes()) != artifact.content_hash:
            raise InfrastructureError("Stored report artifact integrity check failed")
        return artifact, path


report_service = ReportService()
