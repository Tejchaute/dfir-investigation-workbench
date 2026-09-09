from __future__ import annotations

import mmap
from datetime import datetime
from importlib.metadata import version
from typing import Any
from xml.etree import ElementTree

from Evtx.Evtx import FileHeader  # type: ignore[import-untyped]

from app.domain.enums import ArtifactType, ParserExecutionStatus
from app.forensic.parser import ForensicParser, ParsedRecord, ParserContext, ParserResult

EVTX_LIBRARY_VERSION = version("python-evtx")


class EvtxParser(ForensicParser):
    @property
    def name(self) -> str:
        return "DFIR_EVTX"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def supported_artifact_types(self) -> frozenset[ArtifactType]:
        return frozenset({ArtifactType.EVTX})

    def parse(self, context: ParserContext) -> ParserResult:
        if not self._has_signature(context):
            return ParserResult(
                status=ParserExecutionStatus.UNSUPPORTED,
                errors=("Input does not have an EVTX file signature",),
                metadata=self._metadata(),
            )
        records: list[ParsedRecord] = []
        warnings: list[str] = []
        try:
            with mmap.mmap(context.source.fileno(), 0, access=mmap.ACCESS_READ) as buffer:
                header = FileHeader(buffer, 0)
                for chunk_index, chunk in enumerate(header.chunks()):
                    try:
                        for source_record in chunk.records():
                            try:
                                records.append(self._normalize_record(context, source_record))
                            except Exception as error:
                                identifier = self._safe_record_identifier(source_record)
                                warnings.append(
                                    f"EVTX record {identifier} could not be normalized: "
                                    f"{type(error).__name__}"
                                )
                    except Exception as error:
                        warnings.append(
                            f"EVTX chunk {chunk_index} could not be fully read: "
                            f"{type(error).__name__}"
                        )
        except Exception as error:
            return ParserResult(
                status=ParserExecutionStatus.FAILED,
                errors=(f"EVTX parsing failed: {type(error).__name__}",),
                metadata=self._metadata(),
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
            metadata=self._metadata(event_count=len(records)),
            statistics={
                "event_count": len(records),
                "warning_count": len(warnings),
                "error_count": 0,
            },
        )

    @staticmethod
    def _has_signature(context: ParserContext) -> bool:
        context.source.seek(0)
        signature = context.source.read(8)
        context.source.seek(0)
        return signature == b"ElfFile\x00"

    @staticmethod
    def _normalize_record(context: ParserContext, source_record: Any) -> ParsedRecord:
        xml_text = source_record.xml()
        root = ElementTree.fromstring(xml_text)
        system = _child(root, "System")
        provider_element = _child(system, "Provider")
        event_id_element = _child(system, "EventID")
        timestamp_text = _attribute(_child(system, "TimeCreated"), "SystemTime")
        event_time, timezone_known = _parse_event_time(timestamp_text)
        record_identifier = _text(_child(system, "EventRecordID"))
        provider = _attribute(provider_element, "Name")
        channel = _text(_child(system, "Channel"))
        event_id = _integer(_text(event_id_element))
        event_data = _event_data(root)
        data: dict[str, object] = {
            "provider": provider,
            "provider_guid": _attribute(provider_element, "Guid"),
            "event_id": event_id,
            "event_id_qualifiers": _attribute(event_id_element, "Qualifiers"),
            "channel": channel,
            "computer": _text(_child(system, "Computer")),
            "level": _integer(_text(_child(system, "Level"))),
            "task": _integer(_text(_child(system, "Task"))),
            "opcode": _integer(_text(_child(system, "Opcode"))),
            "keywords": _text(_child(system, "Keywords")),
            "event_version": _integer(_text(_child(system, "Version"))),
            "event_timestamp": timestamp_text,
            "event_timestamp_timezone_known": timezone_known,
            "event_data": event_data,
            "event_xml": xml_text,
        }
        provenance: dict[str, object] = {
            "evidence_id": str(context.evidence_id),
            "event_record_id": record_identifier,
            "event_id": event_id,
            "channel": channel,
            "provider": provider,
        }
        return ParsedRecord(
            record_type="EVTX_EVENT",
            source_record_identifier=record_identifier,
            event_time=event_time,
            data=data,
            provenance=provenance,
        )

    @staticmethod
    def _safe_record_identifier(source_record: Any) -> str:
        try:
            return str(source_record.record_num())
        except Exception:
            return "unknown"

    @staticmethod
    def _metadata(event_count: int | None = None) -> dict[str, object]:
        metadata: dict[str, object] = {
            "source_format": "EVTX",
            "library": "python-evtx",
            "library_version": EVTX_LIBRARY_VERSION,
        }
        if event_count is not None:
            metadata["event_count"] = event_count
        return metadata


def _local_name(element: ElementTree.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _child(parent: ElementTree.Element | None, name: str) -> ElementTree.Element | None:
    if parent is None:
        return None
    return next((element for element in parent if _local_name(element) == name), None)


def _text(element: ElementTree.Element | None) -> str | None:
    if element is None or element.text is None:
        return None
    value = element.text.strip()
    return value or None


def _attribute(element: ElementTree.Element | None, name: str) -> str | None:
    if element is None:
        return None
    value = element.attrib.get(name)
    return value if value not in {None, ""} else None


def _integer(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value, 0)
    except ValueError:
        return None


def _parse_event_time(value: str | None) -> tuple[datetime | None, bool | None]:
    if value is None:
        return None, None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None, False
    return parsed, True


def _event_data(root: ElementTree.Element) -> list[dict[str, str | None]]:
    event_data = _child(root, "EventData")
    if event_data is None:
        return []
    return [
        {"name": element.attrib.get("Name"), "value": element.text}
        for element in event_data
        if _local_name(element) == "Data"
    ]
