import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.correlation.registry import CorrelationRuleRegistry, correlation_rule_registry
from app.correlation.rules import (
    DEFAULT_TEMPORAL_WINDOW_SECONDS,
    EvtxPrefetchRule,
    LnkEvtxRule,
    NtfsEvtxRule,
    RegistryEvtxRule,
)
from app.db.models import TimelineEvent
from app.domain.enums import (
    ArtifactType,
    TimelineEventType,
    TimestampPrecision,
)

CASE_ID = uuid.UUID(int=1)
OTHER_CASE_ID = uuid.UUID(int=2)
BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)


def _event(
    number: int,
    event_type: TimelineEventType,
    artifact_type: ArtifactType,
    metadata: dict[str, object],
    *,
    seconds: int = 0,
    case_id: uuid.UUID = CASE_ID,
    has_time: bool = True,
) -> TimelineEvent:
    return TimelineEvent(
        id=uuid.UUID(int=number),
        case_id=case_id,
        evidence_id=uuid.UUID(int=100 + number),
        artifact_id=uuid.UUID(int=200 + number),
        artifact_record_id=uuid.UUID(int=300 + number),
        parser_name="TEST",
        parser_version="1.0.0",
        artifact_type=artifact_type,
        event_type=event_type,
        event_time=BASE_TIME + timedelta(seconds=seconds) if has_time else None,
        raw_time=None,
        time_source="test.time",
        time_semantics="test observation",
        timestamp_precision=TimestampPrecision.SECOND,
        event_ordinal=0,
        description="Synthetic isolated rule test observation",
        source_identifier=f"source-{number}",
        metadata_=metadata,
        provenance={},
    )


def _process(
    number: int = 1,
    *,
    name: str = "powershell.exe",
    seconds: int = 0,
    case_id: uuid.UUID = CASE_ID,
    has_time: bool = True,
) -> TimelineEvent:
    return _event(
        number,
        TimelineEventType.EVTX_EVENT,
        ArtifactType.EVTX,
        {
            "event_id": 4688,
            "channel": "Security",
            "process_name": name,
            "process_path": f"C:\\Windows\\System32\\{name}",
        },
        seconds=seconds,
        case_id=case_id,
        has_time=has_time,
    )


@pytest.mark.parametrize("seconds,expected", [(0, 1), (300, 1), (-300, 1), (301, 0)])
def test_evtx_prefetch_temporal_boundaries(seconds: int, expected: int) -> None:
    prefetch = _event(
        2,
        TimelineEventType.PREFETCH_EXECUTION,
        ArtifactType.PREFETCH,
        {"application_name": "POWERSHELL.EXE"},
        seconds=seconds,
    )
    result = EvtxPrefetchRule().evaluate((_process(), prefetch), 300)
    assert len(result.candidates) == expected


def test_evtx_prefetch_rejects_identity_time_and_case_gaps() -> None:
    rule = EvtxPrefetchRule()
    mismatched = _event(
        2,
        TimelineEventType.PREFETCH_EXECUTION,
        ArtifactType.PREFETCH,
        {"application_name": "cmd.exe"},
    )
    missing_time = _event(
        3,
        TimelineEventType.PREFETCH_EXECUTION,
        ArtifactType.PREFETCH,
        {"application_name": "powershell.exe"},
        has_time=False,
    )
    other_case = _event(
        4,
        TimelineEventType.PREFETCH_EXECUTION,
        ArtifactType.PREFETCH,
        {"application_name": "powershell.exe"},
        case_id=OTHER_CASE_ID,
    )
    missing_identity = _process(5, name="")
    matching = _event(
        6,
        TimelineEventType.PREFETCH_EXECUTION,
        ArtifactType.PREFETCH,
        {"application_name": "powershell.exe"},
    )
    assert not rule.evaluate((_process(), mismatched), 300).candidates
    assert not rule.evaluate((_process(), missing_time), 300).candidates
    assert not rule.evaluate((_process(), other_case), 300).candidates
    assert not rule.evaluate((missing_identity, matching), 300).candidates


def test_lnk_rule_prefers_exact_path_and_records_basename_fallback() -> None:
    exact = _event(
        2,
        TimelineEventType.LNK_METADATA_MODIFICATION,
        ArtifactType.LNK,
        {"target_path": "c:/windows/system32/POWERSHELL.EXE"},
        seconds=300,
    )
    basename = _event(
        3,
        TimelineEventType.LNK_METADATA_CREATION,
        ArtifactType.LNK,
        {"target_path": "powershell.exe"},
        seconds=-300,
    )
    result = LnkEvtxRule().evaluate((_process(), exact, basename), 300)
    assert [candidate.match_basis for candidate in result.candidates] == [
        "basename_match",
        "exact_path_match",
    ]
    assert (
        not LnkEvtxRule()
        .evaluate(
            (
                _process(),
                _event(
                    4,
                    TimelineEventType.LNK_METADATA_ACCESS,
                    ArtifactType.LNK,
                    {"target_path": "C:\\Tools\\cmd.exe"},
                ),
            ),
            300,
        )
        .candidates
    )
    outside = _event(
        5,
        TimelineEventType.LNK_METADATA_MODIFICATION,
        ArtifactType.LNK,
        {"target_path": "C:\\Windows\\System32\\powershell.exe"},
        seconds=301,
    )
    assert not LnkEvtxRule().evaluate((_process(), outside), 300).candidates


def test_lnk_rule_does_not_fallback_when_full_paths_disagree() -> None:
    different_full_path = _event(
        6,
        TimelineEventType.LNK_METADATA_CREATION,
        ArtifactType.LNK,
        {"target_path": "D:\\Tools\\powershell.exe"},
    )

    assert not LnkEvtxRule().evaluate((_process(), different_full_path), 300).candidates


def test_ntfs_rule_requires_exact_filename_identity_and_time() -> None:
    ntfs = _event(
        2,
        TimelineEventType.NTFS_SI_MODIFICATION,
        ArtifactType.NTFS_MFT,
        {"filename": "POWERSHELL.EXE"},
        seconds=300,
    )
    result = NtfsEvtxRule().evaluate((_process(), ntfs), 300)
    assert len(result.candidates) == 1
    assert result.candidates[0].match_basis == "basename_match"
    unrelated = _event(
        3,
        TimelineEventType.NTFS_FN_MODIFICATION,
        ArtifactType.NTFS_MFT,
        {"filename": "document.txt"},
        seconds=1,
    )
    outside = _event(
        4,
        TimelineEventType.NTFS_FN_ACCESS,
        ArtifactType.NTFS_MFT,
        {"filename": "powershell.exe"},
        seconds=301,
    )
    assert not NtfsEvtxRule().evaluate((_process(), unrelated, outside), 300).candidates


def test_registry_rule_is_explicitly_inactive_without_process_identity() -> None:
    registry = _event(
        2,
        TimelineEventType.REGISTRY_KEY_LAST_WRITE,
        ArtifactType.REGISTRY,
        {"hive": "SOFTWARE", "key_path": "ROOT\\Software\\powershell.exe"},
    )
    result = RegistryEvtxRule().evaluate((_process(), registry), 300)
    assert not result.candidates
    assert "does not contain an explicit executable identity" in result.warnings[0]


def test_registry_is_deterministic_and_rejects_duplicates() -> None:
    rules = correlation_rule_registry.rules()
    assert [rule.rule_id for rule in rules] == sorted(rule.rule_id for rule in rules)
    registry = CorrelationRuleRegistry()
    registry.register(EvtxPrefetchRule())
    with pytest.raises(ValueError, match="already registered"):
        registry.register(EvtxPrefetchRule())


def test_default_window_is_explicit_five_minutes() -> None:
    assert DEFAULT_TEMPORAL_WINDOW_SECONDS == 300
