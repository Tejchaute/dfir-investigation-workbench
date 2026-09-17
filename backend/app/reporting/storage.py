from __future__ import annotations

import os
import uuid
from contextlib import suppress
from pathlib import Path

from app.core.exceptions import InfrastructureError


class ReportStorage:
    def __init__(self, report_root: Path, evidence_root: Path) -> None:
        self.root = report_root.resolve()
        evidence = evidence_root.resolve()
        if self.root == evidence or self.root in evidence.parents or evidence in self.root.parents:
            raise InfrastructureError("Report and evidence storage roots must be separate")

    def paths(self, case_id: uuid.UUID, report_id: uuid.UUID, extension: str) -> tuple[Path, Path]:
        directory = self._controlled(self.root / "cases" / str(case_id) / str(report_id))
        return directory / "snapshot.json", directory / f"report.{extension}"

    def write_new(self, path: Path, content: bytes) -> None:
        controlled = self._controlled(path)
        controlled.parent.mkdir(parents=True, exist_ok=True)
        temporary = controlled.with_name(f".{controlled.name}.{uuid.uuid4()}.tmp")
        try:
            with temporary.open("xb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            if controlled.exists():
                raise InfrastructureError("Report destination already exists")
            temporary.replace(controlled)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise

    def resolve(self, relative_path: str) -> Path:
        if Path(relative_path).is_absolute():
            raise InfrastructureError("Stored report reference is invalid")
        path = self._controlled(self.root / relative_path)
        if not path.is_file() or path.is_symlink():
            raise InfrastructureError("Stored report artifact is unavailable")
        return path

    def relative(self, path: Path) -> str:
        return self._controlled(path).relative_to(self.root).as_posix()

    def cleanup_operation(self, report_id: uuid.UUID, paths: tuple[Path, ...]) -> None:
        for path in paths:
            if str(report_id) in path.parts and self._controlled(path).exists():
                path.unlink()
        directories = sorted(
            {path.parent for path in paths}, key=lambda item: len(item.parts), reverse=True
        )
        for directory in directories:
            if str(report_id) in directory.parts:
                with suppress(OSError):
                    directory.rmdir()

    def _controlled(self, path: Path) -> Path:
        resolved = path.resolve()
        if resolved != self.root and self.root not in resolved.parents:
            raise InfrastructureError("Report path escapes configured storage")
        return resolved
