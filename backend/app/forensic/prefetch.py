from __future__ import annotations

from datetime import datetime

from app.domain.enums import ArtifactType, ParserExecutionStatus
from app.forensic.parser import ForensicParser, ParsedRecord, ParserContext, ParserResult
from app.forensic.windows_binary import StructureError, filetime, uint32, uint64, utf16_fixed

SUPPORTED_VERSIONS = frozenset({17, 23, 26, 30, 31})
HEADER_SIZE = 84
MAX_PREFETCH_SIZE = 64 * 1024 * 1024


class PrefetchParser(ForensicParser):
    @property
    def name(self) -> str:
        return "DFIR_PREFETCH"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def supported_artifact_types(self) -> frozenset[ArtifactType]:
        return frozenset({ArtifactType.PREFETCH})

    def parse(self, context: ParserContext) -> ParserResult:
        context.source.seek(0)
        prefix = context.source.read(8)
        context.source.seek(0)
        if prefix[:3] == b"MAM":
            return self._unsupported("Compressed Prefetch files are not supported")
        if len(prefix) < 8 or prefix[4:8] != b"SCCA":
            return self._unsupported("Input does not have a Prefetch signature")
        version = int.from_bytes(prefix[:4], "little")
        if version not in SUPPORTED_VERSIONS:
            return self._unsupported(f"Prefetch version {version} is not supported", version)
        try:
            context.source.seek(0)
            data = context.source.read(MAX_PREFETCH_SIZE + 1)
            if len(data) > MAX_PREFETCH_SIZE:
                raise StructureError("Prefetch input exceeds the safe structure size limit")
            record, warnings = self._normalize(context, data, version)
        except (StructureError, UnicodeError, ValueError) as error:
            return ParserResult(
                status=ParserExecutionStatus.FAILED,
                errors=(f"Prefetch parsing failed: {type(error).__name__}",),
                metadata=self._metadata(version),
            )
        status = (
            ParserExecutionStatus.COMPLETED_WITH_WARNINGS
            if warnings
            else ParserExecutionStatus.COMPLETED
        )
        return ParserResult(
            status=status,
            records=(record,),
            warnings=tuple(warnings),
            metadata=self._metadata(version),
            statistics={"record_count": 1, "warning_count": len(warnings), "error_count": 0},
        )

    def _normalize(
        self, context: ParserContext, data: bytes, version: int
    ) -> tuple[ParsedRecord, list[str]]:
        if len(data) < HEADER_SIZE:
            raise StructureError("Prefetch header is truncated")
        declared_size = uint32(data, 12)
        if declared_size and declared_size > len(data):
            raise StructureError("Prefetch declared size exceeds available bytes")
        warnings: list[str] = []
        if declared_size and declared_size != len(data):
            warnings.append("Prefetch declared size differs from stored byte count")
        application_name = utf16_fixed(data[16:76])
        executable_hash = f"{uint32(data, 76):08x}"
        filename_offset = uint32(data, 100)
        filename_size = uint32(data, 104)
        referenced_paths = self._paths(data, filename_offset, filename_size, warnings)
        volume_offset = uint32(data, 108)
        volume_count = uint32(data, 112)
        volumes = self._volumes(data, volume_offset, volume_count, version, warnings)
        execution_times, run_count = self._execution(data, version, warnings)
        observed_times = [item for item in execution_times if item[1] is not None]
        normalized_times = [
            item[0].isoformat() if item[0] is not None else None for item in observed_times
        ]
        raw_times = [item[1] for item in observed_times]
        evidence_identifier = str(context.evidence_id)
        source_identifier = context.source_name or evidence_identifier
        return (
            ParsedRecord(
                record_type="PREFETCH_FILE",
                source_record_identifier=source_identifier,
                event_time=None,
                data={
                    "artifact_type": ArtifactType.PREFETCH.value,
                    "source_identifier": source_identifier,
                    "source_prefetch_filename": context.source_name,
                    "application_name": application_name,
                    "executable_hash": executable_hash,
                    "prefetch_version": version,
                    "run_count": run_count,
                    "execution_times": normalized_times,
                    "execution_time_filetime_values": raw_times,
                    "referenced_paths": referenced_paths,
                    "volume_information": volumes,
                    "declared_file_size": declared_size,
                },
                provenance={
                    "evidence_id": evidence_identifier,
                    "source_prefetch_filename": context.source_name,
                },
            ),
            warnings,
        )

    @staticmethod
    def _execution(
        data: bytes, version: int, warnings: list[str]
    ) -> tuple[list[tuple[datetime | None, str | None]], int | None]:
        count = 1 if version in {17, 23} else 8
        offset = 120 if version == 17 else 128
        count_offset = {17: 144, 23: 152, 26: 208, 30: 208, 31: 208}[version]
        try:
            timestamps = [filetime(uint64(data, offset + index * 8)) for index in range(count)]
            run_count = uint32(data, count_offset)
        except StructureError:
            warnings.append("Prefetch execution metadata is truncated")
            return [], None
        if any(parsed is None and raw is not None for parsed, raw in timestamps):
            warnings.append("One or more Prefetch execution FILETIMEs could not be represented")
        return timestamps, run_count

    @staticmethod
    def _paths(data: bytes, offset: int, size: int, warnings: list[str]) -> list[str]:
        if not size:
            return []
        if offset < HEADER_SIZE or offset + size > len(data):
            warnings.append("Prefetch referenced-path section is invalid")
            return []
        try:
            text = data[offset : offset + size].decode("utf-16-le")
        except UnicodeError:
            warnings.append("Prefetch referenced-path section is not valid UTF-16LE")
            return []
        return sorted({value for value in text.split("\x00") if value}, key=str.casefold)

    @staticmethod
    def _volumes(
        data: bytes, offset: int, count: int, version: int, warnings: list[str]
    ) -> list[dict[str, object]]:
        if not count:
            return []
        if count > 128 or offset < HEADER_SIZE or offset >= len(data):
            warnings.append("Prefetch volume section is invalid")
            return []
        volumes: list[dict[str, object]] = []
        entry_size = {17: 40, 23: 104, 26: 96, 30: 96, 31: 96}[version]
        for index in range(count):
            entry = offset + index * entry_size
            try:
                path_offset = uint32(data, entry)
                path_chars = uint32(data, entry + 4)
                created, created_raw = filetime(uint64(data, entry + 8))
                serial = uint32(data, entry + 16)
                start = offset + path_offset
                end = start + path_chars * 2
                if start < offset or end > len(data):
                    raise StructureError("volume path is outside Prefetch data")
                path = data[start:end].decode("utf-16-le")
                volumes.append(
                    {
                        "device_path": path,
                        "creation_time": created.isoformat() if created else None,
                        "creation_time_filetime": created_raw,
                        "serial_number": f"{serial:08x}",
                    }
                )
            except (StructureError, UnicodeError):
                warnings.append(f"Prefetch volume entry {index} could not be decoded")
        return volumes

    @staticmethod
    def _metadata(version: int | None = None) -> dict[str, object]:
        return {
            "source_format": "WINDOWS_PREFETCH",
            "format_version": version,
            "implementation": "focused-structure-parser",
        }

    def _unsupported(self, message: str, version: int | None = None) -> ParserResult:
        return ParserResult(
            status=ParserExecutionStatus.UNSUPPORTED,
            errors=(message,),
            metadata=self._metadata(version),
        )
