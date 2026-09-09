from __future__ import annotations

import uuid

from app.domain.enums import ArtifactType, ParserExecutionStatus
from app.forensic.parser import ForensicParser, ParsedRecord, ParserContext, ParserResult
from app.forensic.windows_binary import (
    StructureError,
    c_string,
    filetime,
    uint16,
    uint32,
    uint64,
)

SHELL_LINK_CLSID = bytes.fromhex("0114020000000000c000000000000046")
HEADER_SIZE = 0x4C
MAX_IDLIST_ITEMS = 4096
MAX_LNK_SIZE = 64 * 1024 * 1024

FLAG_NAMES = {
    0: "HAS_LINK_TARGET_ID_LIST",
    1: "HAS_LINK_INFO",
    2: "HAS_NAME",
    3: "HAS_RELATIVE_PATH",
    4: "HAS_WORKING_DIR",
    5: "HAS_ARGUMENTS",
    6: "HAS_ICON_LOCATION",
    7: "IS_UNICODE",
    8: "FORCE_NO_LINK_INFO",
    9: "HAS_EXP_STRING",
    10: "RUN_IN_SEPARATE_PROCESS",
    12: "HAS_DARWIN_ID",
    13: "RUN_AS_USER",
    14: "HAS_EXP_ICON",
    15: "NO_PIDL_ALIAS",
    17: "RUN_WITH_SHIM_LAYER",
    18: "FORCE_NO_LINK_TRACK",
    19: "ENABLE_TARGET_METADATA",
    20: "DISABLE_LINK_PATH_TRACKING",
    21: "DISABLE_KNOWN_FOLDER_TRACKING",
    22: "DISABLE_KNOWN_FOLDER_ALIAS",
    23: "ALLOW_LINK_TO_LINK",
    24: "UNALIAS_ON_SAVE",
    25: "PREFER_ENVIRONMENT_PATH",
    26: "KEEP_LOCAL_ID_LIST_FOR_UNC_TARGET",
}


class LnkParser(ForensicParser):
    @property
    def name(self) -> str:
        return "DFIR_LNK"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def supported_artifact_types(self) -> frozenset[ArtifactType]:
        return frozenset({ArtifactType.LNK})

    def parse(self, context: ParserContext) -> ParserResult:
        context.source.seek(0)
        data = context.source.read(MAX_LNK_SIZE + 1)
        if len(data) < 20 or data[4:20] != SHELL_LINK_CLSID:
            return ParserResult(
                status=ParserExecutionStatus.UNSUPPORTED,
                errors=("Input does not have a Shell Link CLSID",),
                metadata=self._metadata(),
            )
        try:
            if len(data) > MAX_LNK_SIZE:
                raise StructureError("Shell Link exceeds the safe structure size limit")
            record, warnings = self._normalize(context, data)
        except (StructureError, UnicodeError, ValueError) as error:
            return ParserResult(
                status=ParserExecutionStatus.FAILED,
                errors=(f"Shell Link parsing failed: {type(error).__name__}",),
                metadata=self._metadata(),
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
            metadata=self._metadata(),
            statistics={"record_count": 1, "warning_count": len(warnings), "error_count": 0},
        )

    def _normalize(self, context: ParserContext, data: bytes) -> tuple[ParsedRecord, list[str]]:
        if len(data) < HEADER_SIZE or uint32(data, 0) != HEADER_SIZE:
            raise StructureError("invalid Shell Link header size")
        flags = uint32(data, 20)
        attributes = uint32(data, 24)
        warnings: list[str] = []
        creation = self._timestamp(data, 28, warnings, "creation")
        access = self._timestamp(data, 36, warnings, "access")
        modification = self._timestamp(data, 44, warnings, "modification")
        offset = HEADER_SIZE
        shell_items: list[dict[str, object]] = []
        if flags & 1:
            id_list_size = uint16(data, offset)
            offset += 2
            end = offset + id_list_size
            if end > len(data):
                raise StructureError("Shell Link target IDList is truncated")
            shell_items = self._id_list(data[offset:end], warnings)
            offset = end
        link_info: dict[str, object] = {}
        if flags & 2:
            link_info, offset = self._link_info(data, offset, warnings)
        strings: dict[str, str | None] = {}
        unicode = bool(flags & (1 << 7))
        for bit, name in (
            (2, "description"),
            (3, "relative_path"),
            (4, "working_directory"),
            (5, "command_line_arguments"),
            (6, "icon_location"),
        ):
            if flags & (1 << bit):
                value, offset = self._string_data(data, offset, unicode)
                strings[name] = value
            else:
                strings[name] = None
        tracker, extra_warnings = self._extra_data(data, offset)
        warnings.extend(extra_warnings)
        evidence_identifier = str(context.evidence_id)
        source_identifier = context.source_name or evidence_identifier
        target_path = self._target_path(link_info, strings)
        data_fields: dict[str, object] = {
            "artifact_type": ArtifactType.LNK.value,
            "source_identifier": source_identifier,
            "source_lnk_filename": context.source_name,
            "target_path": target_path,
            **strings,
            "link_flags": [name for bit, name in FLAG_NAMES.items() if flags & (1 << bit)],
            "link_flags_raw": flags,
            "file_attributes": attributes,
            "creation_time": creation[0],
            "creation_time_filetime": creation[1],
            "access_time": access[0],
            "access_time_filetime": access[1],
            "modification_time": modification[0],
            "modification_time_filetime": modification[1],
            "target_file_size": uint32(data, 52),
            "icon_index": uint32(data, 56),
            "show_command": uint32(data, 60),
            "target_id_list": shell_items,
            "volume_information": link_info.get("volume_information"),
            "local_path": link_info.get("local_base_path"),
            "common_path_suffix": link_info.get("common_path_suffix"),
            "network_information": link_info.get("network_information"),
            "tracker_information": tracker,
        }
        return (
            ParsedRecord(
                record_type="SHELL_LINK",
                source_record_identifier=source_identifier,
                event_time=None,
                data=data_fields,
                provenance={
                    "evidence_id": evidence_identifier,
                    "source_lnk_filename": context.source_name,
                },
            ),
            warnings,
        )

    @staticmethod
    def _timestamp(
        data: bytes, offset: int, warnings: list[str], name: str
    ) -> tuple[str | None, str | None]:
        parsed, raw = filetime(uint64(data, offset))
        if parsed is None and raw is not None:
            warnings.append(f"Shell Link {name} FILETIME could not be represented")
        return parsed.isoformat() if parsed else None, raw

    @staticmethod
    def _string_data(data: bytes, offset: int, unicode: bool) -> tuple[str, int]:
        characters = uint16(data, offset)
        offset += 2
        byte_count = characters * 2 if unicode else characters
        end = offset + byte_count
        if end > len(data):
            raise StructureError("Shell Link StringData is truncated")
        encoding = "utf-16-le" if unicode else "cp1252"
        return data[offset:end].decode(encoding), end

    @staticmethod
    def _id_list(data: bytes, warnings: list[str]) -> list[dict[str, object]]:
        items: list[dict[str, object]] = []
        offset = 0
        while offset + 2 <= len(data):
            size = uint16(data, offset)
            if size == 0:
                return items
            if size < 2 or offset + size > len(data):
                warnings.append("Shell Item IDList contains a malformed item")
                return items
            item = data[offset : offset + size]
            class_type = item[2] if len(item) > 2 else None
            class_group = (class_type & 0x70) if class_type is not None else None
            class_names = {
                0x10: "ROOT_FOLDER",
                0x20: "VOLUME",
                0x30: "FILE_ENTRY",
                0x40: "NETWORK_LOCATION",
                0x60: "URI",
            }
            class_name = class_names.get(class_group) if class_group is not None else None
            items.append(
                {
                    "index": len(items),
                    "size": size,
                    "class_type": class_type,
                    "class_name": class_name,
                    "bounded_header_hex": item[2:18].hex(),
                }
            )
            if class_name is None:
                warnings.append(
                    f"Shell Item {len(items) - 1} has an unsupported class type; "
                    "bounded source metadata was preserved"
                )
            if len(items) >= MAX_IDLIST_ITEMS:
                warnings.append("Shell Item IDList exceeded the safe item limit")
                return items
            offset += size
        if offset != len(data):
            warnings.append("Shell Item IDList has trailing bytes")
        return items

    @staticmethod
    def _link_info(data: bytes, offset: int, warnings: list[str]) -> tuple[dict[str, object], int]:
        size = uint32(data, offset)
        if size < 0x1C or offset + size > len(data):
            raise StructureError("Shell Link LinkInfo is invalid")
        block = data[offset : offset + size]
        header_size = uint32(block, 4)
        flags = uint32(block, 8)
        if header_size < 0x1C or header_size > size:
            raise StructureError("Shell Link LinkInfo header is invalid")
        local_offset = uint32(block, 16)
        network_offset = uint32(block, 20)
        suffix_offset = uint32(block, 24)
        local_unicode = uint32(block, 28) if header_size >= 0x24 else 0
        suffix_unicode = uint32(block, 32) if header_size >= 0x24 else 0
        result: dict[str, object] = {
            "flags": flags,
            "local_base_path": c_string(
                block, local_unicode or local_offset, unicode=bool(local_unicode)
            ),
            "common_path_suffix": c_string(
                block, suffix_unicode or suffix_offset, unicode=bool(suffix_unicode)
            ),
        }
        volume_offset = uint32(block, 12)
        if flags & 1 and volume_offset:
            try:
                result["volume_information"] = LnkParser._volume(block, volume_offset)
            except (StructureError, UnicodeError):
                warnings.append("Shell Link volume information could not be decoded")
        if flags & 2 and network_offset:
            try:
                result["network_information"] = LnkParser._network(block, network_offset)
            except (StructureError, UnicodeError):
                warnings.append("Shell Link network information could not be decoded")
        return result, offset + size

    @staticmethod
    def _volume(block: bytes, offset: int) -> dict[str, object]:
        size = uint32(block, offset)
        if size < 16 or offset + size > len(block):
            raise StructureError("VolumeID is invalid")
        volume = block[offset : offset + size]
        label_offset = uint32(volume, 12)
        unicode_offset = uint32(volume, 16) if label_offset == 0x14 else 0
        return {
            "drive_type": uint32(volume, 4),
            "drive_serial_number": f"{uint32(volume, 8):08x}",
            "volume_label": c_string(
                volume, unicode_offset or label_offset, unicode=bool(unicode_offset)
            ),
        }

    @staticmethod
    def _network(block: bytes, offset: int) -> dict[str, object]:
        size = uint32(block, offset)
        if size < 20 or offset + size > len(block):
            raise StructureError("CommonNetworkRelativeLink is invalid")
        network = block[offset : offset + size]
        net_offset = uint32(network, 8)
        device_offset = uint32(network, 12)
        unicode_net = uint32(network, 20) if net_offset > 0x14 and size >= 28 else 0
        unicode_device = uint32(network, 24) if net_offset > 0x14 and size >= 28 else 0
        return {
            "flags": uint32(network, 4),
            "network_share_name": c_string(
                network, unicode_net or net_offset, unicode=bool(unicode_net)
            ),
            "device_name": c_string(
                network, unicode_device or device_offset, unicode=bool(unicode_device)
            ),
            "network_provider_type": uint32(network, 16),
        }

    @staticmethod
    def _extra_data(data: bytes, offset: int) -> tuple[dict[str, object] | None, list[str]]:
        tracker: dict[str, object] | None = None
        warnings: list[str] = []
        while offset + 4 <= len(data):
            size = uint32(data, offset)
            if size == 0:
                return tracker, warnings
            if size < 8 or offset + size > len(data):
                warnings.append("Shell Link ExtraData contains a malformed block")
                return tracker, warnings
            signature = uint32(data, offset + 4)
            if signature == 0xA0000003 and size >= 96:
                block = data[offset : offset + size]
                tracker = {
                    "machine_id": block[16:32]
                    .split(b"\x00", 1)[0]
                    .decode("cp1252", errors="replace"),
                    "droid_volume_identifier": str(uuid.UUID(bytes_le=block[32:48])),
                    "droid_file_identifier": str(uuid.UUID(bytes_le=block[48:64])),
                    "birth_droid_volume_identifier": str(uuid.UUID(bytes_le=block[64:80])),
                    "birth_droid_file_identifier": str(uuid.UUID(bytes_le=block[80:96])),
                }
            offset += size
        if offset != len(data):
            warnings.append("Shell Link ExtraData terminator is missing")
        return tracker, warnings

    @staticmethod
    def _target_path(link_info: dict[str, object], strings: dict[str, str | None]) -> str | None:
        local = link_info.get("local_base_path")
        suffix = link_info.get("common_path_suffix")
        if isinstance(local, str):
            if isinstance(suffix, str) and suffix and not local.endswith(suffix):
                return f"{local.rstrip('\\')}\\{suffix.lstrip('\\')}"
            return local
        network = link_info.get("network_information")
        if isinstance(network, dict):
            share = network.get("network_share_name")
            if isinstance(share, str):
                return (
                    f"{share.rstrip('\\')}\\{suffix.lstrip('\\')}"
                    if isinstance(suffix, str) and suffix
                    else share
                )
        return strings.get("relative_path")

    @staticmethod
    def _metadata() -> dict[str, object]:
        return {"source_format": "WINDOWS_SHELL_LINK", "implementation": "MS-SHLLINK"}
