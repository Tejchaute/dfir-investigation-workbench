from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from app.db.models import Artifact, ArtifactRecord
from app.domain.enums import ArtifactType, TimelineEventType, TimestampPrecision


@dataclass(frozen=True)
class NormalizedTimelineEvent:
    event_type: TimelineEventType
    event_time: datetime | None
    raw_time: str | None
    time_source: str
    time_semantics: str
    timestamp_precision: TimestampPrecision
    event_ordinal: int
    description: str
    source_identifier: str | None
    metadata: dict[str, object]
    provenance: dict[str, object]


@dataclass(frozen=True)
class NormalizationResult:
    events: tuple[NormalizedTimelineEvent, ...] = ()
    warnings: tuple[str, ...] = ()
    supported: bool = True


class TimelineNormalizer:
    """Explicit ArtifactRecord-to-timeline mappings without inference or correlation."""

    def normalize(self, artifact: Artifact, record: ArtifactRecord) -> NormalizationResult:
        mapping = {
            ArtifactType.EVTX: self._evtx,
            ArtifactType.REGISTRY: self._registry,
            ArtifactType.PREFETCH: self._prefetch,
            ArtifactType.LNK: self._lnk,
            ArtifactType.NTFS_MFT: self._ntfs,
        }.get(artifact.artifact_type)
        if mapping is None:
            return NormalizationResult(supported=False)
        return mapping(record)

    def _evtx(self, record: ArtifactRecord) -> NormalizationResult:
        if record.record_type != "EVTX_EVENT":
            return NormalizationResult()
        data = record.data
        raw_time = _string(data.get("event_timestamp"))
        event_time = _aware(record.event_time) or _aware_iso(raw_time)
        if raw_time is None:
            return NormalizationResult(warnings=("EVTX record has no source event timestamp",))
        event_id = data.get("event_id")
        channel = _string(data.get("channel")) or "unknown channel"
        return NormalizationResult(
            events=(
                NormalizedTimelineEvent(
                    event_type=TimelineEventType.EVTX_EVENT,
                    event_time=event_time,
                    raw_time=raw_time,
                    time_source="evtx.system.time_created",
                    time_semantics="Windows event source timestamp",
                    timestamp_precision=_iso_precision(raw_time),
                    event_ordinal=0,
                    description=_description(f"Windows event {event_id} observed from {channel}"),
                    source_identifier=record.source_record_identifier,
                    metadata={
                        "event_record_id": record.source_record_identifier,
                        "provider": data.get("provider"),
                        "event_id": event_id,
                        "channel": data.get("channel"),
                        "computer": data.get("computer"),
                        "level": data.get("level"),
                    },
                    provenance=dict(record.provenance),
                ),
            )
        )

    def _registry(self, record: ArtifactRecord) -> NormalizationResult:
        if record.record_type != "REGISTRY_KEY":
            return NormalizationResult()
        data = record.data
        raw_time = _string(data.get("key_last_write_time"))
        if raw_time is None:
            return NormalizationResult(warnings=("Registry key has no LastWrite timestamp",))
        key_path = _string(data.get("key_path")) or "unknown key"
        return NormalizationResult(
            events=(
                NormalizedTimelineEvent(
                    event_type=TimelineEventType.REGISTRY_KEY_LAST_WRITE,
                    event_time=_aware(record.event_time) or _aware_iso(raw_time),
                    raw_time=raw_time,
                    time_source="registry.key_last_write",
                    time_semantics="Registry key metadata LastWrite timestamp",
                    timestamp_precision=_iso_precision(raw_time),
                    event_ordinal=0,
                    description=_description(
                        f"Registry key LastWrite timestamp observed for {key_path}"
                    ),
                    source_identifier=record.source_record_identifier,
                    metadata={"hive": data.get("hive_type"), "key_path": data.get("key_path")},
                    provenance=dict(record.provenance),
                ),
            )
        )

    def _prefetch(self, record: ArtifactRecord) -> NormalizationResult:
        if record.record_type != "PREFETCH_FILE":
            return NormalizationResult()
        data = record.data
        times = _list(data.get("execution_times"))
        raw_times = _list(data.get("execution_time_filetime_values"))
        if not raw_times and not times:
            return NormalizationResult(warnings=("Prefetch record has no execution timestamp",))
        count = max(len(times), len(raw_times))
        application = _string(data.get("application_name")) or "unknown application"
        events: list[NormalizedTimelineEvent] = []
        warnings: list[str] = []
        for index in range(count):
            normalized = _string(times[index]) if index < len(times) else None
            raw = _string(raw_times[index]) if index < len(raw_times) else None
            if normalized is None and raw is None:
                warnings.append(f"Prefetch execution timestamp {index} is empty")
                continue
            events.append(
                NormalizedTimelineEvent(
                    event_type=TimelineEventType.PREFETCH_EXECUTION,
                    event_time=_aware_iso(normalized),
                    raw_time=raw,
                    time_source=f"prefetch.execution_time[{index}]",
                    time_semantics="Prefetch execution-related metadata timestamp",
                    timestamp_precision=(
                        TimestampPrecision.HUNDRED_NANOSECOND
                        if raw is not None
                        else _iso_precision(normalized)
                    ),
                    event_ordinal=index,
                    description=_description(
                        f"Prefetch execution-related timestamp observed for {application}"
                    ),
                    source_identifier=record.source_record_identifier,
                    metadata={
                        "application_name": data.get("application_name"),
                        "executable_hash": data.get("executable_hash"),
                        "prefetch_filename": data.get("source_prefetch_filename"),
                        "run_count": data.get("run_count"),
                    },
                    provenance=dict(record.provenance),
                )
            )
        return NormalizationResult(events=tuple(events), warnings=tuple(warnings))

    def _lnk(self, record: ArtifactRecord) -> NormalizationResult:
        if record.record_type != "SHELL_LINK":
            return NormalizationResult()
        data = record.data
        definitions = (
            (
                "creation",
                TimelineEventType.LNK_METADATA_CREATION,
                "Shell Link creation metadata timestamp",
            ),
            (
                "access",
                TimelineEventType.LNK_METADATA_ACCESS,
                "Shell Link access metadata timestamp",
            ),
            (
                "modification",
                TimelineEventType.LNK_METADATA_MODIFICATION,
                "Shell Link modification metadata timestamp",
            ),
        )
        events: list[NormalizedTimelineEvent] = []
        for ordinal, (field, event_type, semantics) in enumerate(definitions):
            normalized = _string(data.get(f"{field}_time"))
            raw = _string(data.get(f"{field}_time_filetime"))
            if normalized is None and raw is None:
                continue
            events.append(
                NormalizedTimelineEvent(
                    event_type=event_type,
                    event_time=_aware_iso(normalized),
                    raw_time=raw,
                    time_source=f"lnk.header.{field}_time",
                    time_semantics=semantics,
                    timestamp_precision=(
                        TimestampPrecision.HUNDRED_NANOSECOND
                        if raw is not None
                        else _iso_precision(normalized)
                    ),
                    event_ordinal=ordinal,
                    description=_description(f"{semantics} observed for Shell Link target"),
                    source_identifier=record.source_record_identifier,
                    metadata={
                        "target_path": data.get("target_path"),
                        "relative_path": data.get("relative_path"),
                        "source_lnk_filename": data.get("source_lnk_filename"),
                    },
                    provenance=dict(record.provenance),
                )
            )
        return NormalizationResult(events=tuple(events))

    def _ntfs(self, record: ArtifactRecord) -> NormalizationResult:
        if record.record_type != "NTFS_MFT_RECORD":
            return NormalizationResult()
        data = record.data
        events: list[NormalizedTimelineEvent] = []
        standard = _dict(data.get("standard_information"))
        if standard:
            events.extend(
                self._ntfs_family(
                    record,
                    data,
                    standard,
                    family="$STANDARD_INFORMATION",
                    prefix="NTFS_SI",
                    filename=_first_filename(data),
                    parent=None,
                    ordinal=0,
                )
            )
        for ordinal, file_name in enumerate(_dict_list(data.get("file_names"))):
            events.extend(
                self._ntfs_family(
                    record,
                    data,
                    file_name,
                    family="$FILE_NAME",
                    prefix="NTFS_FN",
                    filename=_string(file_name.get("filename")),
                    parent=file_name.get("parent_directory_reference"),
                    ordinal=ordinal,
                )
            )
        return NormalizationResult(events=tuple(events))

    @staticmethod
    def _ntfs_family(
        record: ArtifactRecord,
        record_data: dict[str, object],
        timestamps: dict[str, object],
        *,
        family: str,
        prefix: str,
        filename: str | None,
        parent: object,
        ordinal: int,
    ) -> list[NormalizedTimelineEvent]:
        fields = (
            ("creation_time", "CREATION", "creation"),
            ("modification_time", "MODIFICATION", "modification"),
            ("mft_change_time", "MFT_CHANGE", "MFT change"),
            ("access_time", "ACCESS", "access"),
        )
        events: list[NormalizedTimelineEvent] = []
        display_name = filename or f"MFT record {record_data.get('record_number')}"
        for field, suffix, description_name in fields:
            normalized = _string(timestamps.get(field))
            raw = _string(timestamps.get(f"{field}_filetime"))
            if normalized is None and raw is None:
                continue
            event_type = TimelineEventType[f"{prefix}_{suffix}"]
            events.append(
                NormalizedTimelineEvent(
                    event_type=event_type,
                    event_time=_aware_iso(normalized),
                    raw_time=raw,
                    time_source=f"{family}.{field}",
                    time_semantics=(
                        "NTFS standard information metadata timestamp"
                        if family == "$STANDARD_INFORMATION"
                        else "NTFS filename metadata timestamp"
                    ),
                    timestamp_precision=(
                        TimestampPrecision.HUNDRED_NANOSECOND
                        if raw is not None
                        else _iso_precision(normalized)
                    ),
                    event_ordinal=ordinal,
                    description=_description(
                        f"NTFS {family} {description_name} timestamp for {display_name}"
                    ),
                    source_identifier=record.source_record_identifier,
                    metadata={
                        "record_number": record_data.get("record_number"),
                        "filename": filename,
                        "parent_directory_reference": parent,
                        "source_record_offset": record_data.get("source_record_offset"),
                        "timestamp_family": family,
                        "timestamp_field": field,
                    },
                    provenance=dict(record.provenance),
                )
            )
        return events


def _aware(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is None or value.utcoffset() is None:
        return None
    return value


def _aware_iso(value: str | None) -> datetime | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return _aware(parsed)


def _iso_precision(value: str | None) -> TimestampPrecision:
    if value is None:
        return TimestampPrecision.UNKNOWN
    match = re.search(r"T\d{2}:\d{2}:\d{2}(?:\.(\d+))?", value)
    if match is None:
        return TimestampPrecision.UNKNOWN
    digits = match.group(1)
    if digits is None:
        return TimestampPrecision.SECOND
    return {
        3: TimestampPrecision.MILLISECOND,
        6: TimestampPrecision.MICROSECOND,
        7: TimestampPrecision.HUNDRED_NANOSECOND,
    }.get(len(digits), TimestampPrecision.UNKNOWN)


def _string(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _dict_list(value: object) -> list[dict[str, object]]:
    return [item for item in _list(value) if isinstance(item, dict)]


def _first_filename(data: dict[str, object]) -> str | None:
    names = _dict_list(data.get("file_names"))
    return _string(names[0].get("filename")) if names else None


def _description(value: str) -> str:
    return value[:1000]


timeline_normalizer = TimelineNormalizer()
