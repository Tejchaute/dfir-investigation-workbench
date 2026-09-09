import hashlib
import io
import uuid
from pathlib import Path
from typing import Any

import pytest

from app.domain.enums import ArtifactType, EvidenceType, ParserExecutionStatus
from app.forensic.evtx import EvtxParser
from app.forensic.parser import ParserContext
from tests.support.phase5_fixtures import materialize_fixture


def _context(source: Any) -> ParserContext:
    return ParserContext(uuid.uuid4(), uuid.uuid4(), EvidenceType.LOG_FILE, source)


def test_evtx_parser_normalizes_real_offline_event_without_mutation(tmp_path: Path) -> None:
    path = tmp_path / "source.evtx"
    content = materialize_fixture("evtx_issue38.evtx.gz.b64", path)
    digest_before = hashlib.sha256(content).hexdigest()

    with path.open("rb") as source:
        result = EvtxParser().parse(_context(source))

    assert result.status is ParserExecutionStatus.COMPLETED
    assert result.metadata["library_version"] == "0.8.1"
    assert result.statistics == {"event_count": 1, "warning_count": 0, "error_count": 0}
    record = result.records[0]
    assert record.record_type == "EVTX_EVENT"
    assert record.source_record_identifier == "17845"
    assert record.data["provider"] == "Microsoft-Windows-Security-Auditing"
    assert record.data["event_id"] == 4672
    assert record.data["channel"] == "Security"
    assert record.data["event_timestamp_timezone_known"] is True
    assert record.event_time is not None and record.event_time.utcoffset() is not None
    assert record.provenance["evidence_id"]
    assert record.provenance["event_record_id"] == "17845"
    assert "<Event" in str(record.data["event_xml"])
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest_before


@pytest.mark.parametrize(
    ("content", "status"),
    [
        (b"not an evtx", ParserExecutionStatus.UNSUPPORTED),
        (b"ElfFile\x00broken", ParserExecutionStatus.FAILED),
    ],
)
def test_evtx_parser_distinguishes_unsupported_and_malformed(
    tmp_path: Path, content: bytes, status: ParserExecutionStatus
) -> None:
    path = tmp_path / "input.evtx"
    path.write_bytes(content)
    with path.open("rb") as source:
        result = EvtxParser().parse(_context(source))
    assert result.status is status
    assert result.errors
    assert not result.records


def test_evtx_parser_contract_and_supported_type() -> None:
    parser = EvtxParser()
    assert parser.name == "DFIR_EVTX"
    assert parser.version == "1.0.0"
    assert parser.supported_artifact_types == frozenset({ArtifactType.EVTX})


def test_evtx_requires_file_backed_controlled_source() -> None:
    result = EvtxParser().parse(_context(io.BytesIO(b"ElfFile\x00")))
    assert result.status is ParserExecutionStatus.FAILED
    assert result.errors == ("EVTX parsing failed: UnsupportedOperation",)


def test_evtx_preserves_record_warning_and_continues(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    valid_xml = """<Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event">
      <System><Provider Name="Provider"/><EventID>1</EventID><EventRecordID>2</EventRecordID>
      <TimeCreated SystemTime="2020-01-01T00:00:00Z"/></System></Event>"""

    class FakeRecord:
        def __init__(self, identifier: int, xml: str) -> None:
            self.identifier = identifier
            self._xml = xml

        def record_num(self) -> int:
            return self.identifier

        def xml(self) -> str:
            return self._xml

    class FakeChunk:
        def records(self) -> list[FakeRecord]:
            return [FakeRecord(1, "not xml"), FakeRecord(2, valid_xml)]

    class FakeHeader:
        def __init__(self, _buffer: object, _offset: int) -> None:
            pass

        def chunks(self) -> list[FakeChunk]:
            return [FakeChunk()]

    monkeypatch.setattr("app.forensic.evtx.FileHeader", FakeHeader)
    path = tmp_path / "fixture.evtx"
    path.write_bytes(b"ElfFile\x00")
    with path.open("rb") as source:
        result = EvtxParser().parse(_context(source))
    assert result.status is ParserExecutionStatus.COMPLETED_WITH_WARNINGS
    assert len(result.records) == 1
    assert result.records[0].source_record_identifier == "2"
    assert result.warnings == ("EVTX record 1 could not be normalized: ParseError",)
