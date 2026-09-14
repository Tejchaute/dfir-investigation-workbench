from __future__ import annotations

import ntpath
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from app.db.models import TimelineEvent
from app.domain.enums import (
    FindingConfidence,
    FindingSeverity,
    FindingType,
    TimelineEventType,
)

DEFAULT_TEMPORAL_WINDOW_SECONDS = 300
RULE_SET_VERSION = "1.0.0"


@dataclass(frozen=True)
class CorrelationCandidate:
    rule_id: str
    rule_version: str
    event_a: TimelineEvent
    event_b: TimelineEvent
    event_a_role: str
    event_b_role: str
    temporal_delta_seconds: float
    signed_delta_seconds: float
    match_basis: str
    matched_fields: tuple[str, ...]
    normalized_identity: str
    explanation: str
    finding_type: FindingType
    finding_title: str
    finding_description: str
    severity: FindingSeverity
    confidence: FindingConfidence


@dataclass(frozen=True)
class RuleEvaluation:
    candidates: tuple[CorrelationCandidate, ...] = ()
    warnings: tuple[str, ...] = ()


class CorrelationRule(ABC):
    rule_id: str
    version = "1.0.0"
    name: str
    description: str
    required_event_types: frozenset[TimelineEventType]

    @abstractmethod
    def evaluate(
        self, events: tuple[TimelineEvent, ...], temporal_window_seconds: int
    ) -> RuleEvaluation:
        """Return deterministic matches over timeline observations only."""


class EvtxPrefetchRule(CorrelationRule):
    rule_id = "CORR-EVTX-PREFETCH-001"
    name = "Process Creation and Prefetch Corroboration"
    description = "Matches Security 4688 process identity to Prefetch application identity."
    required_event_types = frozenset(
        {TimelineEventType.EVTX_EVENT, TimelineEventType.PREFETCH_EXECUTION}
    )

    def evaluate(
        self, events: tuple[TimelineEvent, ...], temporal_window_seconds: int
    ) -> RuleEvaluation:
        process_events = _process_events(events)
        prefetch = [
            event for event in events if event.event_type == TimelineEventType.PREFETCH_EXECUTION
        ]
        candidates: list[CorrelationCandidate] = []
        for process, observed, identity in _identity_time_pairs(
            process_events,
            prefetch,
            left_identity=lambda event: _name(event.metadata_.get("process_name")),
            right_identity=lambda event: _name(event.metadata_.get("application_name")),
            window=temporal_window_seconds,
        ):
            delta, signed = _delta(process, observed)
            candidates.append(
                CorrelationCandidate(
                    rule_id=self.rule_id,
                    rule_version=self.version,
                    event_a=process,
                    event_b=observed,
                    event_a_role="process_creation",
                    event_b_role="prefetch_execution_observation",
                    temporal_delta_seconds=delta,
                    signed_delta_seconds=signed,
                    match_basis="basename_match",
                    matched_fields=("process_name", "application_name"),
                    normalized_identity=identity,
                    explanation=(
                        f"Security Event 4688 process identity '{identity}' matched Prefetch "
                        f"execution identity within {temporal_window_seconds} seconds."
                    ),
                    finding_type=FindingType.PROCESS_EXECUTION_CORROBORATED,
                    finding_title="Process creation correlated with Prefetch execution",
                    finding_description=_finding_description(
                        "Security Event 4688 recorded a process-creation identity.",
                        f"Prefetch execution-related metadata for the same executable basename "
                        f"was observed {delta:g} seconds apart.",
                    ),
                    severity=FindingSeverity.MEDIUM,
                    confidence=FindingConfidence.MEDIUM,
                )
            )
        return RuleEvaluation(tuple(candidates))


class LnkEvtxRule(CorrelationRule):
    rule_id = "CORR-LNK-EVTX-001"
    name = "LNK Target and Process Creation Association"
    description = "Matches a Shell Link target to a Security 4688 process identity."
    required_event_types = frozenset(
        {
            TimelineEventType.EVTX_EVENT,
            TimelineEventType.LNK_METADATA_CREATION,
            TimelineEventType.LNK_METADATA_ACCESS,
            TimelineEventType.LNK_METADATA_MODIFICATION,
        }
    )

    def evaluate(
        self, events: tuple[TimelineEvent, ...], temporal_window_seconds: int
    ) -> RuleEvaluation:
        process_events = _process_events(events)
        lnk_events = [
            event for event in events if event.event_type.name.startswith("LNK_METADATA_")
        ]
        candidates: list[CorrelationCandidate] = []
        for process, lnk, identity in _identity_time_pairs(
            process_events,
            lnk_events,
            left_identity=lambda event: _name(event.metadata_.get("process_name")),
            right_identity=lambda event: _basename(event.metadata_.get("target_path")),
            window=temporal_window_seconds,
        ):
            process_path = _full_path(process.metadata_.get("process_path"))
            target_path = _full_path(lnk.metadata_.get("target_path"))
            if process_path is not None and target_path is not None and process_path != target_path:
                continue
            exact = (
                process_path is not None and target_path is not None and process_path == target_path
            )
            basis = "exact_path_match" if exact else "basename_match"
            fields = (
                ("process_path", "target_path") if exact else ("process_name", "target_basename")
            )
            delta, signed = _delta(process, lnk)
            candidates.append(
                CorrelationCandidate(
                    rule_id=self.rule_id,
                    rule_version=self.version,
                    event_a=process,
                    event_b=lnk,
                    event_a_role="process_creation",
                    event_b_role="lnk_metadata_observation",
                    temporal_delta_seconds=delta,
                    signed_delta_seconds=signed,
                    match_basis=basis,
                    matched_fields=fields,
                    normalized_identity=(
                        process_path if exact and process_path is not None else identity
                    ),
                    explanation=(
                        f"LNK target and Security Event 4688 process identity matched by {basis} "
                        f"within {temporal_window_seconds} seconds."
                    ),
                    finding_type=FindingType.LNK_PROCESS_ASSOCIATION,
                    finding_title="LNK target correlated with process creation",
                    finding_description=_finding_description(
                        "A Shell Link target and Security Event 4688 process identity "
                        "were observed.",
                        f"Their {basis.replace('_', ' ')} was observed {delta:g} seconds apart.",
                    ),
                    severity=FindingSeverity.LOW,
                    confidence=(FindingConfidence.HIGH if exact else FindingConfidence.MEDIUM),
                )
            )
        return RuleEvaluation(tuple(candidates))


class NtfsEvtxRule(CorrelationRule):
    rule_id = "CORR-NTFS-EVTX-001"
    name = "NTFS Metadata and Process Activity Association"
    description = "Matches an NTFS filename observation to a Security 4688 process identity."
    required_event_types = frozenset(
        {
            TimelineEventType.EVTX_EVENT,
            TimelineEventType.NTFS_SI_CREATION,
            TimelineEventType.NTFS_SI_MODIFICATION,
            TimelineEventType.NTFS_SI_MFT_CHANGE,
            TimelineEventType.NTFS_SI_ACCESS,
            TimelineEventType.NTFS_FN_CREATION,
            TimelineEventType.NTFS_FN_MODIFICATION,
            TimelineEventType.NTFS_FN_MFT_CHANGE,
            TimelineEventType.NTFS_FN_ACCESS,
        }
    )

    def evaluate(
        self, events: tuple[TimelineEvent, ...], temporal_window_seconds: int
    ) -> RuleEvaluation:
        process_events = _process_events(events)
        ntfs_events = [event for event in events if event.event_type.name.startswith("NTFS_")]
        candidates: list[CorrelationCandidate] = []
        for process, ntfs, identity in _identity_time_pairs(
            process_events,
            ntfs_events,
            left_identity=lambda event: _name(event.metadata_.get("process_name")),
            right_identity=lambda event: _basename(event.metadata_.get("filename")),
            window=temporal_window_seconds,
        ):
            process_path = _path(process.metadata_.get("process_path"))
            file_path = _path(ntfs.metadata_.get("full_path"))
            exact = process_path is not None and file_path is not None and process_path == file_path
            basis = "exact_path_match" if exact else "basename_match"
            fields = ("process_path", "full_path") if exact else ("process_name", "filename")
            delta, signed = _delta(process, ntfs)
            candidates.append(
                CorrelationCandidate(
                    rule_id=self.rule_id,
                    rule_version=self.version,
                    event_a=process,
                    event_b=ntfs,
                    event_a_role="process_creation",
                    event_b_role="ntfs_metadata_observation",
                    temporal_delta_seconds=delta,
                    signed_delta_seconds=signed,
                    match_basis=basis,
                    matched_fields=fields,
                    normalized_identity=(
                        process_path if exact and process_path is not None else identity
                    ),
                    explanation=(
                        f"NTFS filename metadata and Security Event 4688 process identity matched "
                        f"by {basis} within {temporal_window_seconds} seconds."
                    ),
                    finding_type=FindingType.FILE_ACTIVITY_ASSOCIATION,
                    finding_title="NTFS file metadata correlated with process activity",
                    finding_description=_finding_description(
                        "NTFS file metadata and Security Event 4688 process identity "
                        "were observed.",
                        f"Their {basis.replace('_', ' ')} was observed {delta:g} seconds apart.",
                    ),
                    severity=FindingSeverity.LOW,
                    confidence=(FindingConfidence.HIGH if exact else FindingConfidence.MEDIUM),
                )
            )
        return RuleEvaluation(tuple(candidates))


class RegistryEvtxRule(CorrelationRule):
    rule_id = "CORR-REGISTRY-EVTX-001"
    name = "Registry LastWrite and Process Activity Association"
    description = "Requires an explicit Registry executable identity not currently normalized."
    required_event_types = frozenset(
        {TimelineEventType.EVTX_EVENT, TimelineEventType.REGISTRY_KEY_LAST_WRITE}
    )

    def evaluate(
        self, events: tuple[TimelineEvent, ...], temporal_window_seconds: int
    ) -> RuleEvaluation:
        del events, temporal_window_seconds
        return RuleEvaluation(
            warnings=(
                f"{self.rule_id} produced no matches because Registry timeline metadata does not "
                "contain an explicit executable identity.",
            )
        )


def _process_events(events: tuple[TimelineEvent, ...]) -> list[TimelineEvent]:
    return [
        event
        for event in events
        if event.event_type == TimelineEventType.EVTX_EVENT
        and event.metadata_.get("event_id") == 4688
        and isinstance(event.metadata_.get("channel"), str)
        and str(event.metadata_["channel"]).casefold() == "security"
        and (_name(event.metadata_.get("process_name")) is not None)
        and event.event_time is not None
    ]


def _identity_time_pairs(
    left: list[TimelineEvent],
    right: list[TimelineEvent],
    *,
    left_identity: Callable[[TimelineEvent], str | None],
    right_identity: Callable[[TimelineEvent], str | None],
    window: int,
) -> list[tuple[TimelineEvent, TimelineEvent, str]]:
    grouped: dict[str, list[TimelineEvent]] = {}
    for event in right:
        if event.event_time is None:
            continue
        identity = right_identity(event)
        if isinstance(identity, str):
            grouped.setdefault(identity, []).append(event)
    pairs: list[tuple[TimelineEvent, TimelineEvent, str]] = []
    for event in sorted(left, key=_event_sort_key):
        identity = left_identity(event)
        if not isinstance(identity, str):
            continue
        for other in sorted(grouped.get(identity, []), key=_event_sort_key):
            if event.case_id == other.case_id and _within_window(event, other, window):
                pairs.append((event, other, identity))
    return pairs


def _within_window(left: TimelineEvent, right: TimelineEvent, seconds: int) -> bool:
    if left.event_time is None or right.event_time is None:
        return False
    return abs((right.event_time - left.event_time).total_seconds()) <= seconds


def _delta(left: TimelineEvent, right: TimelineEvent) -> tuple[float, float]:
    assert left.event_time is not None and right.event_time is not None
    signed = (right.event_time - left.event_time).total_seconds()
    return abs(signed), signed


def _path(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return ntpath.normpath(value.strip().replace("/", "\\")).casefold()


def _basename(value: object) -> str | None:
    normalized = _path(value)
    return ntpath.basename(normalized) if normalized else None


def _full_path(value: object) -> str | None:
    normalized = _path(value)
    return normalized if normalized is not None and ntpath.isabs(normalized) else None


def _name(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return ntpath.basename(value.strip().replace("/", "\\")).casefold()


def _event_sort_key(event: TimelineEvent) -> tuple[datetime, str, str, int, str]:
    assert event.event_time is not None
    return (
        event.event_time,
        event.source_identifier or "",
        event.time_source,
        event.event_ordinal,
        str(event.id),
    )


def _finding_description(observation: str, correlation: str) -> str:
    return (
        f"Observation: {observation} Correlation: {correlation} "
        "Limitation: This establishes deterministic identity and temporal consistency only; "
        "it does not establish malicious intent, user intent, or causality. "
        "Examiner review is required."
    )
