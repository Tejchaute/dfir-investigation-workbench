import uuid
from pathlib import Path

import pytest

from app.core.exceptions import InfrastructureError
from app.reporting.storage import ReportStorage


def test_report_storage_is_separate_controlled_and_non_overwriting(tmp_path: Path) -> None:
    storage = ReportStorage(tmp_path / "exports", tmp_path / "evidence")
    snapshot, output = storage.paths(uuid.UUID(int=1), uuid.UUID(int=2), "html")
    storage.write_new(output, b"report")
    assert storage.resolve(storage.relative(output)).read_bytes() == b"report"
    with pytest.raises(InfrastructureError, match="already exists"):
        storage.write_new(output, b"replacement")
    with pytest.raises(InfrastructureError):
        storage.resolve("../evidence/original")
    assert snapshot.parent == output.parent


def test_report_storage_rejects_overlapping_evidence_root(tmp_path: Path) -> None:
    with pytest.raises(InfrastructureError, match="must be separate"):
        ReportStorage(tmp_path / "data", tmp_path / "data" / "evidence")
