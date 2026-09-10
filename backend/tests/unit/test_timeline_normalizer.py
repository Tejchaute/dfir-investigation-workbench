import uuid
from datetime import UTC, datetime

from app.db.models import Artifact, ArtifactRecord
from app.domain.enums import (
    ArtifactType,
    ParserExecutionStatus,
    TimelineEventType,
    TimestampPrecision,
)
from app.services.timeline_normalizer import TimelineNormalizer

EVIDENCE_ID = uuid.UUID(int=1)
ARTIFACT_ID = uuid.UUID(int=2)
RECORD_ID = uuid.UUID(int=3)


def _artifact(artifact_type: ArtifactType) -> Artifact:
    return Artifact(
        id=ARTIFACT_ID,
        evidence_id=EVIDENCE_ID,
        artifact_type=artifact_type,
        parser_name="TEST",
        parser_version="1.0.0",
        status=ParserExecutionStatus.COMPLETED,
        metadata_={},
        warnings=[],
        errors=[],
        statistics={},
    )


def _record(
    record_type: str, data: dict[str, object], event_time: datetime | None = None
) -> ArtifactRecord:
    return ArtifactRecord(
        id=RECORD_ID,
        artifact_id=ARTIFACT_ID,
        record_type=record_type,
        source_record_identifier="source-1",
        event_time=event_time,
        data=data,
        provenance={"source_offset": 42},
    )


def test_evtx_mapping_preserves_timestamp_precision_and_provenance() -> None:
    record = _record(
        "EVTX_EVENT",
        {
            "event_timestamp": "2026-01-02T03:04:05.1234567Z",
            "event_id": 4688,
            "provider": "Provider",
            "channel": "Security",
            "computer": "HOST",
            "level": 4,
        },
        datetime(2026, 1, 2, 3, 4, 5, 123456, tzinfo=UTC),
    )
    result = TimelineNormalizer().normalize(_artifact(ArtifactType.EVTX), record)
    event = result.events[0]
    assert event.event_type is TimelineEventType.EVTX_EVENT
    assert event.raw_time == "2026-01-02T03:04:05.1234567Z"
    assert event.time_source == "evtx.system.time_created"
    assert event.timestamp_precision is TimestampPrecision.HUNDRED_NANOSECOND
    assert event.metadata["event_id"] == 4688
    assert event.provenance == {"source_offset": 42}


def test_registry_maps_only_key_last_write_and_preserves_naive_time() -> None:
    key = _record(
        "REGISTRY_KEY",
        {
            "key_last_write_time": "2026-01-02T03:04:05.123456",
            "key_path": "ROOT\\Software",
            "hive_type": "SOFTWARE",
        },
    )
    result = TimelineNormalizer().normalize(_artifact(ArtifactType.REGISTRY), key)
    event = result.events[0]
    assert event.event_type is TimelineEventType.REGISTRY_KEY_LAST_WRITE
    assert event.event_time is None
    assert event.raw_time == "2026-01-02T03:04:05.123456"
    assert event.timestamp_precision is TimestampPrecision.MICROSECOND
    value = _record("REGISTRY_VALUE", {"key_last_write_time": "2026-01-02T03:04:05Z"})
    assert not TimelineNormalizer().normalize(_artifact(ArtifactType.REGISTRY), value).events


def test_prefetch_creates_one_event_per_execution_filetime() -> None:
    record = _record(
        "PREFETCH_FILE",
        {
            "execution_times": [
                "2026-01-02T03:04:05+00:00",
                "2026-01-01T03:04:05+00:00",
            ],
            "execution_time_filetime_values": ["134000000000000000", "133999000000000000"],
            "application_name": "APP.EXE",
            "executable_hash": "12345678",
            "source_prefetch_filename": "APP.EXE-12345678.pf",
            "run_count": 2,
        },
    )
    result = TimelineNormalizer().normalize(_artifact(ArtifactType.PREFETCH), record)
    assert len(result.events) == 2
    assert [event.event_ordinal for event in result.events] == [0, 1]
    assert [event.time_source for event in result.events] == [
        "prefetch.execution_time[0]",
        "prefetch.execution_time[1]",
    ]
    assert all(event.event_type is TimelineEventType.PREFETCH_EXECUTION for event in result.events)
    assert all(
        event.timestamp_precision is TimestampPrecision.HUNDRED_NANOSECOND
        for event in result.events
    )


def test_lnk_creates_distinct_metadata_events_and_no_execution_event() -> None:
    record = _record(
        "SHELL_LINK",
        {
            "creation_time": "2024-02-01T00:00:00+00:00",
            "creation_time_filetime": "133512192000000000",
            "access_time": "2024-02-02T00:00:00+00:00",
            "access_time_filetime": "133513056000000000",
            "modification_time": "2024-02-03T00:00:00+00:00",
            "modification_time_filetime": "133513920000000000",
            "target_path": "C:\\Tools\\app.exe",
        },
    )
    result = TimelineNormalizer().normalize(_artifact(ArtifactType.LNK), record)
    assert [event.event_type for event in result.events] == [
        TimelineEventType.LNK_METADATA_CREATION,
        TimelineEventType.LNK_METADATA_ACCESS,
        TimelineEventType.LNK_METADATA_MODIFICATION,
    ]
    assert all("EXECUTION" not in event.event_type.value for event in result.events)


def test_ntfs_keeps_all_si_and_fn_timestamp_observations_distinct() -> None:
    def timestamps(year: int) -> dict[str, object]:
        return {
            "creation_time": f"{year}-01-01T00:00:00+00:00",
            "creation_time_filetime": "1",
            "modification_time": f"{year}-01-02T00:00:00+00:00",
            "modification_time_filetime": "2",
            "mft_change_time": f"{year}-01-03T00:00:00+00:00",
            "mft_change_time_filetime": "3",
            "access_time": f"{year}-01-04T00:00:00+00:00",
            "access_time_filetime": "4",
        }

    record = _record(
        "NTFS_MFT_RECORD",
        {
            "record_number": 42,
            "source_record_offset": 1024,
            "standard_information": timestamps(2020),
            "file_names": [
                {
                    **timestamps(2021),
                    "filename": "example.txt",
                    "parent_directory_reference": {"record_number": 5, "sequence_number": 2},
                }
            ],
        },
    )
    result = TimelineNormalizer().normalize(_artifact(ArtifactType.NTFS_MFT), record)
    assert len(result.events) == 8
    assert {event.event_type for event in result.events} == {
        TimelineEventType.NTFS_SI_CREATION,
        TimelineEventType.NTFS_SI_MODIFICATION,
        TimelineEventType.NTFS_SI_MFT_CHANGE,
        TimelineEventType.NTFS_SI_ACCESS,
        TimelineEventType.NTFS_FN_CREATION,
        TimelineEventType.NTFS_FN_MODIFICATION,
        TimelineEventType.NTFS_FN_MFT_CHANGE,
        TimelineEventType.NTFS_FN_ACCESS,
    }
    assert {event.metadata["timestamp_family"] for event in result.events} == {
        "$STANDARD_INFORMATION",
        "$FILE_NAME",
    }
    assert all(
        event.timestamp_precision is TimestampPrecision.HUNDRED_NANOSECOND
        for event in result.events
    )


def test_precision_policy_handles_millisecond_and_unknown() -> None:
    normalizer = TimelineNormalizer()
    millisecond = _record(
        "EVTX_EVENT",
        {"event_timestamp": "2026-01-02T03:04:05.123Z", "event_id": 1, "channel": "System"},
    )
    unknown = _record(
        "EVTX_EVENT",
        {"event_timestamp": "not-a-time", "event_id": 1, "channel": "System"},
    )
    assert (
        normalizer.normalize(_artifact(ArtifactType.EVTX), millisecond)
        .events[0]
        .timestamp_precision
        is TimestampPrecision.MILLISECOND
    )
    unknown_event = normalizer.normalize(_artifact(ArtifactType.EVTX), unknown).events[0]
    assert unknown_event.timestamp_precision is TimestampPrecision.UNKNOWN
    assert unknown_event.event_time is None
