import io
import uuid
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestError, InfrastructureError
from app.db.models import Case
from app.domain.enums import CaseStatus, EvidenceType
from app.schemas.evidence import EvidenceRegistration
from app.services.evidence_service import EvidenceService
from app.services.evidence_storage import COPY_CHUNK_SIZE, EvidenceStorage


class FailingStream(io.BytesIO):
    def __init__(self, content: bytes) -> None:
        super().__init__(content)
        self.reads = 0

    def read(self, size: int | None = -1) -> bytes:
        assert size == COPY_CHUNK_SIZE
        self.reads += 1
        if self.reads > 1:
            raise OSError("synthetic read failure")
        return super().read(2)


def test_storage_streams_copy_and_preserves_source(tmp_path: Path) -> None:
    source_path = tmp_path / "synthetic-source.bin"
    content = b"test-only evidence bytes" * 100
    source_path.write_bytes(content)
    storage = EvidenceStorage(tmp_path / "controlled")
    with source_path.open("rb") as source:
        stored = storage.store(source, uuid.uuid4(), uuid.uuid4())
    assert source_path.read_bytes() == content
    assert stored.absolute_path.read_bytes() == content
    assert stored.size_bytes == len(content)
    assert len(stored.digest) == 64
    assert stored.relative_path.endswith("/original")


@pytest.mark.parametrize(
    "filename", ["../escape.bin", "folder/file.bin", "C:\\escape.bin", "..", ""]
)
def test_storage_rejects_unsafe_filenames(tmp_path: Path, filename: str) -> None:
    storage = EvidenceStorage(tmp_path)
    with pytest.raises(BadRequestError, match="unsafe"):
        storage.validate_filename(filename)


def test_partial_copy_failure_removes_only_operation_artifacts(tmp_path: Path) -> None:
    root = tmp_path / "controlled"
    root.mkdir()
    preexisting = root / "keep.txt"
    preexisting.write_text("keep", encoding="utf-8")
    storage = EvidenceStorage(root)
    with pytest.raises(InfrastructureError, match="storage operation failed"):
        storage.store(FailingStream(b"abcdef"), uuid.uuid4(), uuid.uuid4())
    assert preexisting.read_text(encoding="utf-8") == "keep"
    assert list(root.rglob("*.partial")) == []


def test_resolve_for_read_rejects_escape(tmp_path: Path) -> None:
    storage = EvidenceStorage(tmp_path / "controlled")
    with pytest.raises(InfrastructureError, match="reference is invalid"):
        storage.resolve_for_read("../outside")


def test_database_failure_removes_completed_operation_file(tmp_path: Path) -> None:
    storage = EvidenceStorage(tmp_path / "controlled")
    service = EvidenceService(storage)
    case = Case(
        id=uuid.uuid4(),
        case_number="CASE-2026-TEST",
        name="Synthetic rollback case",
        status=CaseStatus.OPEN,
    )
    session = MagicMock(spec=Session)
    session.scalar.side_effect = [case, 1]
    session.commit.side_effect = SQLAlchemyError("synthetic commit failure")
    payload = EvidenceRegistration(
        evidence_type=EvidenceType.FILE,
        custody_person="Test Custodian",
        collected_at=datetime.now(UTC),
    )

    with pytest.raises(InfrastructureError, match="registration failed"):
        service.register(session, case.id, "synthetic.bin", io.BytesIO(b"test bytes"), payload)

    assert list((tmp_path / "controlled").rglob("original")) == []
    session.rollback.assert_called_once()
