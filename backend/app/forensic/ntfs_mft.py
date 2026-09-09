from __future__ import annotations

from dataclasses import dataclass

from app.domain.enums import ArtifactType, ParserExecutionStatus
from app.forensic.parser import ForensicParser, ParsedRecord, ParserContext, ParserResult
from app.forensic.windows_binary import StructureError, filetime, uint16, uint32, uint64

ATTRIBUTE_NAMES = {
    0x10: "$STANDARD_INFORMATION",
    0x20: "$ATTRIBUTE_LIST",
    0x30: "$FILE_NAME",
    0x40: "$OBJECT_ID",
    0x50: "$SECURITY_DESCRIPTOR",
    0x60: "$VOLUME_NAME",
    0x70: "$VOLUME_INFORMATION",
    0x80: "$DATA",
    0x90: "$INDEX_ROOT",
    0xA0: "$INDEX_ALLOCATION",
    0xB0: "$BITMAP",
    0xC0: "$REPARSE_POINT",
    0xD0: "$EA_INFORMATION",
    0xE0: "$EA",
    0x100: "$LOGGED_UTILITY_STREAM",
}
NAMESPACE_NAMES = {0: "POSIX", 1: "WIN32", 2: "DOS", 3: "WIN32_AND_DOS"}
MAX_RECORD_SIZE = 64 * 1024
MAX_ATTRIBUTES = 1024
MAX_DATA_RUNS = 16384


@dataclass(frozen=True)
class InputLayout:
    kind: str
    first_record_offset: int
    record_size: int
    bytes_per_sector: int | None
    record_limit: int | None = None
    boot_metadata: dict[str, object] | None = None


class NtfsMftParser(ForensicParser):
    @property
    def name(self) -> str:
        return "DFIR_NTFS_MFT"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def supported_artifact_types(self) -> frozenset[ArtifactType]:
        return frozenset({ArtifactType.NTFS_MFT})

    def parse(self, context: ParserContext) -> ParserResult:
        try:
            layout = self._layout(context)
        except StructureError as error:
            message = str(error)
            status = (
                ParserExecutionStatus.UNSUPPORTED
                if message.startswith("unsupported")
                else ParserExecutionStatus.FAILED
            )
            return ParserResult(
                status=status,
                errors=(f"NTFS/MFT parsing failed: {message}",),
                metadata=self._metadata(),
            )
        records: list[ParsedRecord] = []
        warnings: list[str] = []
        if layout.boot_metadata is not None:
            records.append(self._boot_record(context, layout.boot_metadata))
        context.source.seek(0, 2)
        source_size = context.source.tell()
        offset = layout.first_record_offset
        examined = 0
        while offset + layout.record_size <= source_size and (
            layout.record_limit is None or examined < layout.record_limit
        ):
            context.source.seek(offset)
            raw = context.source.read(layout.record_size)
            if raw[:4] == b"\x00\x00\x00\x00":
                offset += layout.record_size
                examined += 1
                continue
            if raw[:4] != b"FILE":
                warnings.append(
                    f"MFT record at byte offset {offset} does not have a FILE signature"
                )
                offset += layout.record_size
                examined += 1
                continue
            try:
                fixed = self._apply_fixup(raw, layout.bytes_per_sector)
                parsed_record, record_warnings = self._record(context, fixed, offset)
                records.append(parsed_record)
                warnings.extend(record_warnings)
            except (StructureError, UnicodeError, ValueError) as error:
                warnings.append(
                    f"MFT record at byte offset {offset} was skipped: "
                    f"{type(error).__name__}: {error}"
                )
            offset += layout.record_size
            examined += 1
        mft_count = sum(record.record_type == "NTFS_MFT_RECORD" for record in records)
        if mft_count == 0:
            return ParserResult(
                status=ParserExecutionStatus.FAILED,
                errors=("NTFS/MFT parsing failed: no valid MFT records were extracted",),
                metadata=self._metadata(layout),
            )
        if layout.record_limit is None and offset != source_size:
            warnings.append("Trailing bytes do not form a complete MFT record")
        status = (
            ParserExecutionStatus.COMPLETED_WITH_WARNINGS
            if warnings
            else ParserExecutionStatus.COMPLETED
        )
        return ParserResult(
            status=status,
            records=tuple(records),
            warnings=tuple(warnings),
            metadata=self._metadata(layout),
            statistics={
                "record_count": len(records),
                "mft_record_count": mft_count,
                "warning_count": len(warnings),
                "error_count": 0,
            },
        )

    @staticmethod
    def _layout(context: ParserContext) -> InputLayout:
        context.source.seek(0)
        prefix = context.source.read(512)
        if len(prefix) >= 72 and prefix[3:11] == b"NTFS    ":
            bytes_per_sector = uint16(prefix, 11)
            sectors_per_cluster = prefix[13]
            if bytes_per_sector < 256 or bytes_per_sector & (bytes_per_sector - 1):
                raise StructureError("invalid NTFS bytes-per-sector value")
            if sectors_per_cluster == 0 or sectors_per_cluster & (sectors_per_cluster - 1):
                raise StructureError("invalid NTFS sectors-per-cluster value")
            cluster_size = bytes_per_sector * sectors_per_cluster
            mft_lcn = uint64(prefix, 48)
            encoded_record_size = int.from_bytes(prefix[64:65], "little", signed=True)
            record_size = (
                1 << -encoded_record_size
                if encoded_record_size < 0
                else encoded_record_size * cluster_size
            )
            if record_size < 512 or record_size > MAX_RECORD_SIZE:
                raise StructureError("invalid NTFS MFT record size")
            return InputLayout(
                kind="NTFS_VOLUME",
                first_record_offset=mft_lcn * cluster_size,
                record_size=record_size,
                bytes_per_sector=bytes_per_sector,
                record_limit=1,
                boot_metadata={
                    "bytes_per_sector": bytes_per_sector,
                    "sectors_per_cluster": sectors_per_cluster,
                    "cluster_size": cluster_size,
                    "mft_logical_cluster_number": mft_lcn,
                    "mft_byte_offset": mft_lcn * cluster_size,
                    "mft_record_size": record_size,
                    "volume_serial_number": f"{uint64(prefix, 72):016x}",
                },
            )
        if prefix[:4] != b"FILE":
            raise StructureError(
                "unsupported input: neither NTFS boot sector nor MFT record stream"
            )
        allocated_size = uint32(prefix, 28)
        if allocated_size < 512 or allocated_size > MAX_RECORD_SIZE:
            raise StructureError("invalid allocated MFT record size")
        usa_count = uint16(prefix, 6)
        sectors = usa_count - 1
        if sectors <= 0 or allocated_size % sectors:
            raise StructureError("invalid MFT update sequence geometry")
        return InputLayout("MFT_STREAM", 0, allocated_size, allocated_size // sectors)

    @staticmethod
    def _apply_fixup(record: bytes, sector_size: int | None) -> bytes:
        usa_offset = uint16(record, 4)
        usa_count = uint16(record, 6)
        if usa_count < 2 or usa_offset < 8 or usa_offset + usa_count * 2 > len(record):
            raise StructureError("invalid update sequence array")
        sectors = usa_count - 1
        derived_sector_size = len(record) // sectors if len(record) % sectors == 0 else 0
        if not derived_sector_size or (
            sector_size is not None and derived_sector_size != sector_size
        ):
            raise StructureError("update sequence geometry does not match record size")
        fixed = bytearray(record)
        sequence = record[usa_offset : usa_offset + 2]
        for index in range(sectors):
            end = (index + 1) * derived_sector_size - 2
            if record[end : end + 2] != sequence:
                raise StructureError(f"update sequence mismatch in sector {index}")
            replacement = record[usa_offset + 2 + index * 2 : usa_offset + 4 + index * 2]
            fixed[end : end + 2] = replacement
        return bytes(fixed)

    def _record(
        self, context: ParserContext, record: bytes, offset: int
    ) -> tuple[ParsedRecord, list[str]]:
        first_attribute = uint16(record, 20)
        used_size = uint32(record, 24)
        allocated_size = uint32(record, 28)
        if first_attribute < 48 or used_size > len(record) or first_attribute >= used_size:
            raise StructureError("invalid MFT record header bounds")
        flags = uint16(record, 22)
        record_number = uint32(record, 44)
        warnings: list[str] = []
        attributes = self._attributes(record, first_attribute, used_size, warnings)
        standard = next(
            (item["parsed"] for item in attributes if item["type"] == "$STANDARD_INFORMATION"),
            None,
        )
        file_names = [item["parsed"] for item in attributes if item["type"] == "$FILE_NAME"]
        data_attributes = [item for item in attributes if item["type"] == "$DATA"]
        attribute_summaries = [
            {key: value for key, value in item.items() if key != "parsed"} for item in attributes
        ]
        base_reference = uint64(record, 32)
        source_identifier = f"mft:{record_number}@{offset}"
        return (
            ParsedRecord(
                record_type="NTFS_MFT_RECORD",
                source_record_identifier=source_identifier,
                event_time=None,
                data={
                    "artifact_type": ArtifactType.NTFS_MFT.value,
                    "record_number": record_number,
                    "sequence_number": uint16(record, 16),
                    "hard_link_count": uint16(record, 18),
                    "flags_raw": flags,
                    "allocated_in_use": bool(flags & 1),
                    "directory": bool(flags & 2),
                    "base_record_reference": self._reference(base_reference),
                    "used_record_size": used_size,
                    "allocated_record_size": allocated_size,
                    "standard_information": standard,
                    "file_names": file_names,
                    "data_attributes": data_attributes,
                    "attributes": attribute_summaries,
                    "source_record_offset": offset,
                },
                provenance={
                    "evidence_id": str(context.evidence_id),
                    "mft_record_number": record_number,
                    "source_record_offset": offset,
                },
            ),
            warnings,
        )

    def _attributes(
        self, record: bytes, offset: int, used_size: int, warnings: list[str]
    ) -> list[dict[str, object]]:
        attributes: list[dict[str, object]] = []
        while offset + 8 <= used_size:
            type_code = uint32(record, offset)
            if type_code == 0xFFFFFFFF:
                return attributes
            length = uint32(record, offset + 4)
            if length < 24 or offset + length > used_size:
                raise StructureError("invalid MFT attribute length")
            non_resident = bool(record[offset + 8])
            name_length = record[offset + 9]
            name_offset = uint16(record, offset + 10)
            name = None
            if name_length:
                end = offset + name_offset + name_length * 2
                if name_offset < 16 or end > offset + length:
                    raise StructureError("invalid MFT attribute name")
                name = record[offset + name_offset : end].decode("utf-16-le")
            item: dict[str, object] = {
                "type_code": f"0x{type_code:08x}",
                "type": ATTRIBUTE_NAMES.get(type_code, "UNKNOWN"),
                "attribute_id": uint16(record, offset + 14),
                "name": name,
                "non_resident": non_resident,
                "flags": uint16(record, offset + 12),
            }
            if non_resident:
                item.update(self._non_resident(record, offset, length))
            else:
                value_length = uint32(record, offset + 16)
                value_offset = uint16(record, offset + 20)
                end = offset + value_offset + value_length
                if value_offset < 24 or end > offset + length:
                    raise StructureError("invalid resident MFT attribute bounds")
                value = record[offset + value_offset : end]
                item["resident_value_length"] = value_length
                if type_code == 0x10:
                    item["parsed"] = self._standard_information(value, warnings)
                elif type_code == 0x30:
                    item["parsed"] = self._file_name(value, warnings)
                elif type_code == 0x80:
                    item["resident_data_length"] = value_length
            attributes.append(item)
            if len(attributes) > MAX_ATTRIBUTES:
                raise StructureError("MFT attribute count exceeds safe limit")
            offset += length
        raise StructureError("MFT attribute terminator is missing")

    @staticmethod
    def _standard_information(value: bytes, warnings: list[str]) -> dict[str, object]:
        if len(value) < 36:
            raise StructureError("$STANDARD_INFORMATION is truncated")
        return {
            **NtfsMftParser._timestamps(value, 0, warnings, "$STANDARD_INFORMATION"),
            "file_attributes": uint32(value, 32),
        }

    @staticmethod
    def _file_name(value: bytes, warnings: list[str]) -> dict[str, object]:
        if len(value) < 66:
            raise StructureError("$FILE_NAME is truncated")
        name_length = value[64]
        end = 66 + name_length * 2
        if end > len(value):
            raise StructureError("$FILE_NAME name is truncated")
        namespace = value[65]
        return {
            "parent_directory_reference": NtfsMftParser._reference(uint64(value, 0)),
            **NtfsMftParser._timestamps(value, 8, warnings, "$FILE_NAME"),
            "allocated_size": uint64(value, 40),
            "logical_size": uint64(value, 48),
            "file_attributes": uint32(value, 56),
            "namespace": NAMESPACE_NAMES.get(namespace, f"UNKNOWN_{namespace}"),
            "filename": value[66:end].decode("utf-16-le"),
        }

    @staticmethod
    def _timestamps(
        value: bytes, offset: int, warnings: list[str], family: str
    ) -> dict[str, object]:
        names = ("creation_time", "modification_time", "mft_change_time", "access_time")
        result: dict[str, object] = {}
        for index, name in enumerate(names):
            parsed, raw = filetime(uint64(value, offset + index * 8))
            result[name] = parsed.isoformat() if parsed else None
            result[f"{name}_filetime"] = raw
            if parsed is None and raw is not None:
                warnings.append(f"{family} {name} FILETIME could not be represented")
        return result

    @staticmethod
    def _non_resident(record: bytes, offset: int, length: int) -> dict[str, object]:
        if length < 64:
            raise StructureError("non-resident MFT attribute is truncated")
        run_offset = uint16(record, offset + 32)
        if run_offset < 64 or run_offset >= length:
            raise StructureError("non-resident data-run offset is invalid")
        return {
            "start_vcn": uint64(record, offset + 16),
            "last_vcn": uint64(record, offset + 24),
            "allocated_size": uint64(record, offset + 40),
            "logical_size": uint64(record, offset + 48),
            "initialized_size": uint64(record, offset + 56),
            "data_runs": NtfsMftParser._data_runs(record[offset + run_offset : offset + length]),
        }

    @staticmethod
    def _data_runs(data: bytes) -> list[dict[str, object]]:
        runs: list[dict[str, object]] = []
        offset = 0
        current_lcn = 0
        while offset < len(data) and data[offset] != 0:
            header = data[offset]
            length_size = header & 0x0F
            offset_size = header >> 4
            offset += 1
            if not length_size or length_size > 8 or offset_size > 8:
                raise StructureError("invalid NTFS data-run header")
            if offset + length_size + offset_size > len(data):
                raise StructureError("NTFS data run is truncated")
            cluster_count = int.from_bytes(data[offset : offset + length_size], "little")
            if cluster_count == 0:
                raise StructureError("NTFS data run has zero clusters")
            offset += length_size
            lcn_delta = None
            lcn = None
            if offset_size:
                lcn_delta = int.from_bytes(
                    data[offset : offset + offset_size], "little", signed=True
                )
                current_lcn += lcn_delta
                lcn = current_lcn
            offset += offset_size
            runs.append(
                {
                    "cluster_count": cluster_count,
                    "lcn": lcn,
                    "lcn_delta": lcn_delta,
                    "sparse": offset_size == 0,
                }
            )
            if len(runs) > MAX_DATA_RUNS:
                raise StructureError("NTFS data-run count exceeds safe limit")
        return runs

    @staticmethod
    def _reference(value: int) -> dict[str, int]:
        return {"record_number": value & 0x0000FFFFFFFFFFFF, "sequence_number": value >> 48}

    @staticmethod
    def _boot_record(context: ParserContext, metadata: dict[str, object]) -> ParsedRecord:
        return ParsedRecord(
            record_type="NTFS_VOLUME",
            source_record_identifier="ntfs:boot-sector",
            data={"artifact_type": ArtifactType.NTFS_MFT.value, **metadata},
            provenance={"evidence_id": str(context.evidence_id), "source_record_offset": 0},
        )

    @staticmethod
    def _metadata(layout: InputLayout | None = None) -> dict[str, object]:
        return {
            "source_format": "NTFS_MFT",
            "input_kind": layout.kind if layout else None,
            "record_size": layout.record_size if layout else None,
            "implementation": "focused-mft-subset-parser",
        }
