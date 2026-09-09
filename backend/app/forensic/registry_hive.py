from __future__ import annotations

import base64
import hashlib
from datetime import datetime
from importlib.metadata import version
from typing import Any

from Registry import Registry  # type: ignore[import-untyped]

from app.domain.enums import ArtifactType, ParserExecutionStatus
from app.forensic.parser import ForensicParser, ParsedRecord, ParserContext, ParserResult

REGISTRY_LIBRARY_VERSION = version("python-registry")
MAX_BINARY_VALUE_BYTES = 4096
SUPPORTED_HIVE_TYPES = frozenset({"NTUSER", "SYSTEM", "SOFTWARE"})


class RegistryHiveParser(ForensicParser):
    @property
    def name(self) -> str:
        return "DFIR_REGISTRY"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def supported_artifact_types(self) -> frozenset[ArtifactType]:
        return frozenset({ArtifactType.REGISTRY})

    def parse(self, context: ParserContext) -> ParserResult:
        if not self._has_signature(context):
            return ParserResult(
                status=ParserExecutionStatus.UNSUPPORTED,
                errors=("Input does not have a Windows Registry hive signature",),
                metadata=self._metadata("UNKNOWN"),
            )
        try:
            context.source.seek(0)
            hive = Registry.Registry(context.source)
            hive_type = hive.hive_type().name
            records, warnings, key_count, value_count = self._walk_hive(
                context, hive.root(), hive_type
            )
        except Exception as error:
            return ParserResult(
                status=ParserExecutionStatus.FAILED,
                errors=(f"Registry parsing failed: {type(error).__name__}",),
                metadata=self._metadata("UNKNOWN"),
            )
        if hive_type not in SUPPORTED_HIVE_TYPES:
            warnings.insert(
                0,
                "Registry hive type could not be identified as NTUSER, SYSTEM, or SOFTWARE",
            )
        status = (
            ParserExecutionStatus.COMPLETED_WITH_WARNINGS
            if warnings
            else ParserExecutionStatus.COMPLETED
        )
        return ParserResult(
            status=status,
            records=tuple(records),
            warnings=tuple(warnings),
            metadata=self._metadata(hive_type, key_count=key_count, value_count=value_count),
            statistics={
                "key_count": key_count,
                "value_count": value_count,
                "warning_count": len(warnings),
                "error_count": 0,
            },
        )

    @staticmethod
    def _has_signature(context: ParserContext) -> bool:
        context.source.seek(0)
        signature = context.source.read(4)
        context.source.seek(0)
        return signature == b"regf"

    def _walk_hive(
        self, context: ParserContext, root: Any, hive_type: str
    ) -> tuple[list[ParsedRecord], list[str], int, int]:
        records: list[ParsedRecord] = []
        warnings: list[str] = []
        key_count = 0
        value_count = 0
        pending = [root]
        while pending:
            key = pending.pop()
            path = str(key.path())
            timestamp = key.timestamp()
            event_time, timestamp_text, timezone_known = _registry_timestamp(timestamp)
            records.append(
                ParsedRecord(
                    record_type="REGISTRY_KEY",
                    source_record_identifier=path,
                    event_time=event_time,
                    data={
                        "hive_type": hive_type,
                        "key_path": path,
                        "parent_key_path": _parent_path(path),
                        "key_last_write_time": timestamp_text,
                        "key_last_write_timezone_known": timezone_known,
                    },
                    provenance={"evidence_id": str(context.evidence_id), "key_path": path},
                )
            )
            key_count += 1
            try:
                values = sorted(
                    key.values(),
                    key=lambda value: (value.name().casefold(), value.name()),
                )
            except Exception as error:
                warnings.append(
                    f"Values for Registry key {path!r} could not be read: {type(error).__name__}"
                )
                values = []
            for value in values:
                try:
                    records.append(
                        self._normalize_value(context, value, hive_type, path, timestamp_text)
                    )
                    value_count += 1
                except Exception as error:
                    warnings.append(
                        f"Registry value under key {path!r} could not be normalized: "
                        f"{type(error).__name__}"
                    )
            try:
                subkeys = sorted(
                    key.subkeys(),
                    key=lambda subkey: (subkey.name().casefold(), subkey.name()),
                    reverse=True,
                )
                pending.extend(subkeys)
            except Exception as error:
                warnings.append(
                    f"Subkeys for Registry key {path!r} could not be read: {type(error).__name__}"
                )
        return records, warnings, key_count, value_count

    @staticmethod
    def _normalize_value(
        context: ParserContext,
        value: Any,
        hive_type: str,
        key_path: str,
        key_timestamp: str | None,
    ) -> ParsedRecord:
        value_name = str(value.name())
        value_type = str(value.value_type_str())
        raw_data = bytes(value.raw_data())
        normalized = _json_value(value.value())
        identifier = f"{key_path}\\{value_name or '(Default)'}"
        return ParsedRecord(
            record_type="REGISTRY_VALUE",
            source_record_identifier=identifier,
            event_time=None,
            data={
                "hive_type": hive_type,
                "key_path": key_path,
                "parent_key_path": _parent_path(key_path),
                "value_name": value_name,
                "value_type": value_type,
                "value_data": normalized,
                "raw_data": _binary_representation(raw_data),
                "key_last_write_time": key_timestamp,
            },
            provenance={
                "evidence_id": str(context.evidence_id),
                "key_path": key_path,
                "value_name": value_name,
            },
        )

    @staticmethod
    def _metadata(
        hive_type: str, key_count: int | None = None, value_count: int | None = None
    ) -> dict[str, object]:
        metadata: dict[str, object] = {
            "source_format": "WINDOWS_REGISTRY_HIVE",
            "hive_type": hive_type,
            "hive_type_supported": hive_type in SUPPORTED_HIVE_TYPES,
            "library": "python-registry",
            "library_version": REGISTRY_LIBRARY_VERSION,
            "binary_encoding": "base64",
            "binary_preview_limit_bytes": MAX_BINARY_VALUE_BYTES,
        }
        if key_count is not None:
            metadata["key_count"] = key_count
        if value_count is not None:
            metadata["value_count"] = value_count
        return metadata


def _registry_timestamp(value: datetime) -> tuple[datetime | None, str, bool]:
    text = value.isoformat()
    if value.tzinfo is None or value.utcoffset() is None:
        return None, text, False
    return value, text, True


def _parent_path(path: str) -> str | None:
    parent, separator, _name = path.rpartition("\\")
    return parent if separator else None


def _binary_representation(value: bytes) -> dict[str, object]:
    preview = value[:MAX_BINARY_VALUE_BYTES]
    return {
        "encoding": "base64",
        "data": base64.b64encode(preview).decode("ascii"),
        "byte_length": len(value),
        "truncated": len(value) > MAX_BINARY_VALUE_BYTES,
        "sha256": hashlib.sha256(value).hexdigest(),
    }


def _json_value(value: object) -> object:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, bytes):
        return _binary_representation(value)
    if isinstance(value, list | tuple):
        return [_json_value(item) for item in value]
    raise TypeError(f"Unsupported Registry value representation: {type(value).__name__}")
