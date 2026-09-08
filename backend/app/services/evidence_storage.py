from __future__ import annotations

import hashlib
import os
import uuid
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from app.core.exceptions import BadRequestError, InfrastructureError

COPY_CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True)
class StoredEvidence:
    relative_path: str
    digest: str
    size_bytes: int
    absolute_path: Path
    created_directories: tuple[Path, ...]


class EvidenceStorage:
    def __init__(self, root: Path) -> None:
        self.root = root

    @staticmethod
    def validate_filename(filename: str | None) -> str:
        if (
            not filename
            or filename.strip() in {"", ".", ".."}
            or "\x00" in filename
            or "/" in filename
            or "\\" in filename
            or Path(filename).is_absolute()
        ):
            raise BadRequestError("Evidence filename is unsafe")
        if len(filename) > 255:
            raise BadRequestError("Evidence filename is too long")
        return filename

    def store(self, source: BinaryIO, case_id: uuid.UUID, evidence_id: uuid.UUID) -> StoredEvidence:
        root = self._prepare_root()
        relative = Path(str(case_id), "evidence", str(evidence_id), "original")
        final_path = root / relative
        created_directories: list[Path] = []
        temp_path = final_path.with_name(f".original.{uuid.uuid4().hex}.partial")
        try:
            self._create_generated_directories(root, final_path.parent, created_directories)
            if final_path.exists() or temp_path.exists():
                raise InfrastructureError("Evidence destination already exists")
            digest = hashlib.sha256()
            size_bytes = 0
            with temp_path.open("xb") as destination:
                while chunk := source.read(COPY_CHUNK_SIZE):
                    digest.update(chunk)
                    destination.write(chunk)
                    size_bytes += len(chunk)
                destination.flush()
                os.fsync(destination.fileno())
            os.link(temp_path, final_path)
            temp_path.unlink()
            if not final_path.is_file():
                raise InfrastructureError("Evidence storage finalization failed")
            return StoredEvidence(
                relative_path=relative.as_posix(),
                digest=digest.hexdigest(),
                size_bytes=size_bytes,
                absolute_path=final_path,
                created_directories=tuple(created_directories),
            )
        except InfrastructureError:
            self.cleanup_paths(temp_path, final_path, created_directories)
            raise
        except (OSError, ValueError) as error:
            self.cleanup_paths(temp_path, final_path, created_directories)
            raise InfrastructureError("Evidence storage operation failed") from error

    def resolve_for_read(self, relative_path: str) -> Path:
        root = self._prepare_root()
        candidate = Path(relative_path)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise InfrastructureError("Stored evidence reference is invalid")
        resolved = (root / candidate).resolve(strict=False)
        if not resolved.is_relative_to(root) or self._contains_symlink(root, resolved):
            raise InfrastructureError("Stored evidence reference is invalid")
        if not resolved.is_file():
            raise InfrastructureError("Stored evidence file is unavailable")
        return resolved

    @staticmethod
    def calculate_sha256(path: Path) -> tuple[str, int]:
        digest = hashlib.sha256()
        size_bytes = 0
        try:
            with path.open("rb") as source:
                while chunk := source.read(COPY_CHUNK_SIZE):
                    digest.update(chunk)
                    size_bytes += len(chunk)
        except OSError as error:
            raise InfrastructureError("Stored evidence could not be read") from error
        return digest.hexdigest(), size_bytes

    @staticmethod
    def cleanup(stored: StoredEvidence) -> None:
        EvidenceStorage.cleanup_paths(None, stored.absolute_path, list(stored.created_directories))

    @staticmethod
    def cleanup_paths(temp: Path | None, final: Path, directories: list[Path]) -> None:
        for path in (temp, final):
            if path is not None:
                with suppress(OSError):
                    path.unlink(missing_ok=True)
        for directory in reversed(directories):
            with suppress(OSError):
                directory.rmdir()

    def _prepare_root(self) -> Path:
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            if self.root.is_symlink():
                raise InfrastructureError("Evidence root must not be a symbolic link")
            return self.root.resolve(strict=True)
        except OSError as error:
            raise InfrastructureError("Evidence storage is unavailable") from error

    @staticmethod
    def _create_generated_directories(root: Path, destination: Path, created: list[Path]) -> None:
        current = root
        for part in destination.relative_to(root).parts:
            current /= part
            if current.exists():
                if current.is_symlink() or not current.is_dir():
                    raise InfrastructureError("Evidence storage path is unsafe")
            else:
                current.mkdir()
                created.append(current)
            if not current.resolve(strict=True).is_relative_to(root):
                raise InfrastructureError("Evidence storage path is unsafe")

    @staticmethod
    def _contains_symlink(root: Path, path: Path) -> bool:
        current = root
        for part in path.relative_to(root).parts:
            current /= part
            if current.is_symlink():
                return True
        return False
