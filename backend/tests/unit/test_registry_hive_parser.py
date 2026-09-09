import base64
import hashlib
import uuid
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from app.domain.enums import ArtifactType, EvidenceType, ParserExecutionStatus
from app.forensic.parser import ParserContext
from app.forensic.registry_hive import MAX_BINARY_VALUE_BYTES, RegistryHiveParser
from tests.support.phase5_fixtures import materialize_fixture


def _context(source: Any) -> ParserContext:
    return ParserContext(uuid.uuid4(), uuid.uuid4(), EvidenceType.REGISTRY_HIVE, source)


def test_registry_parser_traverses_real_offline_hive_without_mutation(tmp_path: Path) -> None:
    path = tmp_path / "source.hive"
    content = materialize_fixture("registry_issue22.hive.gz.b64", path)
    digest_before = hashlib.sha256(content).hexdigest()

    with path.open("rb") as source:
        result = RegistryHiveParser().parse(_context(source))

    assert result.status is ParserExecutionStatus.COMPLETED_WITH_WARNINGS
    assert result.metadata["library_version"] == "1.3.1"
    assert result.metadata["hive_type"] == "UNKNOWN"
    assert result.statistics["key_count"] == 1
    assert result.statistics["value_count"] == 10
    timezone_record = next(
        record for record in result.records if record.data.get("value_name") == "TimeZoneKeyName"
    )
    assert timezone_record.data["value_type"] == "RegSZ"
    assert timezone_record.data["value_data"] == "W. Europe Standard Time"
    assert timezone_record.data["key_path"] == "TimeZoneInformation"
    assert timezone_record.provenance["evidence_id"]
    assert timezone_record.provenance["key_path"] == "TimeZoneInformation"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest_before


class _FakeValue:
    def __init__(self, name: str, value_type: str, value: object, raw: bytes) -> None:
        self._name = name
        self._type = value_type
        self._value = value
        self._raw = raw

    def name(self) -> str:
        return self._name

    def value_type_str(self) -> str:
        return self._type

    def value(self) -> object:
        return self._value

    def raw_data(self) -> bytes:
        return self._raw


class _FakeKey:
    def path(self) -> str:
        return "ROOT\\Software"

    def timestamp(self) -> datetime:
        return datetime(2020, 1, 2, 3, 4, 5, tzinfo=UTC)

    def values(self) -> list[_FakeValue]:
        return [
            _FakeValue("Binary", "RegBin", b"\x00\xff", b"\x00\xff"),
            _FakeValue("Count", "RegDWord", 7, b"\x07\x00\x00\x00"),
            _FakeValue("Name", "RegSZ", "value", b"v\x00a\x00l\x00u\x00e\x00"),
        ]

    def subkeys(self) -> list[object]:
        return []


@pytest.mark.parametrize("hive_type", ["NTUSER", "SYSTEM", "SOFTWARE"])
def test_registry_parser_preserves_supported_hive_types_and_value_types(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hive_type: str
) -> None:
    class FakeHive:
        def __init__(self, _source: object) -> None:
            pass

        def hive_type(self) -> SimpleNamespace:
            return SimpleNamespace(name=hive_type)

        def root(self) -> _FakeKey:
            return _FakeKey()

    monkeypatch.setattr("app.forensic.registry_hive.Registry.Registry", FakeHive)
    path = tmp_path / "fixture.hive"
    path.write_bytes(b"regf synthetic adapter fixture")
    with path.open("rb") as source:
        result = RegistryHiveParser().parse(_context(source))

    assert result.status is ParserExecutionStatus.COMPLETED
    assert result.metadata["hive_type"] == hive_type
    records = {record.data.get("value_name"): record for record in result.records[1:]}
    assert records["Count"].data["value_data"] == 7
    assert records["Name"].data["value_data"] == "value"
    binary = records["Binary"].data["value_data"]
    assert isinstance(binary, dict) and binary["encoding"] == "base64"
    assert base64.b64decode(str(binary["data"])) == b"\x00\xff"
    assert result.records[0].event_time == datetime(2020, 1, 2, 3, 4, 5, tzinfo=UTC)


def test_registry_binary_representation_is_bounded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    binary = b"x" * (MAX_BINARY_VALUE_BYTES + 1)
    monkeypatch.setattr(
        _FakeKey, "values", lambda _self: [_FakeValue("Big", "RegBin", binary, binary)]
    )
    fake_hive = SimpleNamespace(
        hive_type=lambda: SimpleNamespace(name="SYSTEM"), root=lambda: _FakeKey()
    )
    monkeypatch.setattr("app.forensic.registry_hive.Registry.Registry", lambda _source: fake_hive)
    path = tmp_path / "fixture.hive"
    path.write_bytes(b"regf synthetic adapter fixture")
    with path.open("rb") as source:
        result = RegistryHiveParser().parse(_context(source))
    value_data = result.records[1].data["value_data"]
    assert isinstance(value_data, dict)
    assert value_data["truncated"] is True
    assert len(base64.b64decode(str(value_data["data"]))) == MAX_BINARY_VALUE_BYTES
    assert value_data["sha256"] == hashlib.sha256(binary).hexdigest()


@pytest.mark.parametrize(
    ("content", "status"),
    [
        (b"not a hive", ParserExecutionStatus.UNSUPPORTED),
        (b"regfbroken", ParserExecutionStatus.FAILED),
    ],
)
def test_registry_parser_distinguishes_unsupported_and_malformed(
    tmp_path: Path, content: bytes, status: ParserExecutionStatus
) -> None:
    path = tmp_path / "input.hive"
    path.write_bytes(content)
    with path.open("rb") as source:
        result = RegistryHiveParser().parse(_context(source))
    assert result.status is status
    assert result.errors
    assert not result.records


def test_registry_parser_contract_and_supported_type() -> None:
    parser = RegistryHiveParser()
    assert parser.name == "DFIR_REGISTRY"
    assert parser.version == "1.0.0"
    assert parser.supported_artifact_types == frozenset({ArtifactType.REGISTRY})


def test_registry_preserves_malformed_value_warning_and_continues(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class BrokenValue(_FakeValue):
        def raw_data(self) -> bytes:
            raise ValueError("synthetic malformed value")

    monkeypatch.setattr(
        _FakeKey,
        "values",
        lambda _self: [
            BrokenValue("Broken", "RegBin", b"", b""),
            _FakeValue("Good", "RegDWord", 1, b"\x01\x00\x00\x00"),
        ],
    )
    fake_hive = SimpleNamespace(
        hive_type=lambda: SimpleNamespace(name="SOFTWARE"), root=lambda: _FakeKey()
    )
    monkeypatch.setattr("app.forensic.registry_hive.Registry.Registry", lambda _source: fake_hive)
    path = tmp_path / "fixture.hive"
    path.write_bytes(b"regf synthetic adapter fixture")
    with path.open("rb") as source:
        result = RegistryHiveParser().parse(_context(source))
    assert result.status is ParserExecutionStatus.COMPLETED_WITH_WARNINGS
    assert len(result.records) == 2
    assert result.warnings == (
        "Registry value under key 'ROOT\\\\Software' could not be normalized: ValueError",
    )
