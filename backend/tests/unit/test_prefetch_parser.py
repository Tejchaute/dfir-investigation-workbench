import hashlib
import io
import uuid

import pytest

from app.domain.enums import ArtifactType, EvidenceType, ParserExecutionStatus
from app.forensic.parser import ParserContext, ParserResult
from app.forensic.prefetch import PrefetchParser
from tests.support.phase6_fixtures import prefetch_fixture


def _parse(content: bytes) -> ParserResult:
    source = io.BytesIO(content)
    context = ParserContext(uuid.UUID(int=1), uuid.UUID(int=2), EvidenceType.FILE, source)
    return PrefetchParser().parse(context)


def test_prefetch_parses_supported_structure_deterministically() -> None:
    content = prefetch_fixture()
    digest = hashlib.sha256(content).hexdigest()
    first = _parse(content)
    second = _parse(content)
    assert first.status is ParserExecutionStatus.COMPLETED
    assert first.model_dump() == second.model_dump()
    record = first.records[0]
    assert record.data["application_name"] == "APP.EXE"
    assert record.data["prefetch_version"] == 30
    assert record.data["executable_hash"] == "1234abcd"
    assert record.data["run_count"] == 7
    assert isinstance(record.data["execution_times"], list)
    assert len(record.data["execution_times"]) == 2
    assert isinstance(record.data["referenced_paths"], list)
    assert "C:\\WINDOWS\\SYSTEM32\\KERNEL32.DLL" in record.data["referenced_paths"]
    volumes = record.data["volume_information"]
    assert isinstance(volumes, list) and volumes[0]["serial_number"] == "a1b2c3d4"
    assert hashlib.sha256(content).hexdigest() == digest


def test_prefetch_contract_malformed_and_unsupported_versions() -> None:
    parser = PrefetchParser()
    assert parser.name == "DFIR_PREFETCH" and parser.version == "1.0.0"
    assert parser.supported_artifact_types == frozenset({ArtifactType.PREFETCH})
    assert _parse(b"arbitrary").status is ParserExecutionStatus.UNSUPPORTED
    assert _parse(b"MAM\x04compressed").status is ParserExecutionStatus.UNSUPPORTED
    unsupported = _parse(prefetch_fixture(version=99))
    assert unsupported.status is ParserExecutionStatus.UNSUPPORTED
    malformed = bytearray(prefetch_fixture())
    malformed[12:16] = (9999).to_bytes(4, "little")
    assert _parse(bytes(malformed)).status is ParserExecutionStatus.FAILED


@pytest.mark.parametrize("version", [17, 23, 26, 30, 31])
def test_prefetch_supported_version_layouts(version: int) -> None:
    result = _parse(prefetch_fixture(version=version))
    assert result.status is ParserExecutionStatus.COMPLETED
    assert result.records[0].data["prefetch_version"] == version
    assert result.records[0].data["run_count"] == 7


def test_prefetch_optional_section_problem_is_warning() -> None:
    malformed = bytearray(prefetch_fixture())
    malformed[100:104] = (5000).to_bytes(4, "little")
    result = _parse(bytes(malformed))
    assert result.status is ParserExecutionStatus.COMPLETED_WITH_WARNINGS
    assert result.records and result.warnings
