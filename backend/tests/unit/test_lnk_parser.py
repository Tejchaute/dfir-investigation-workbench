import hashlib
import io
import uuid

from app.domain.enums import ArtifactType, EvidenceType, ParserExecutionStatus
from app.forensic.lnk import LnkParser
from app.forensic.parser import ParserContext, ParserResult
from tests.support.phase6_fixtures import lnk_fixture


def _parse(content: bytes) -> ParserResult:
    source = io.BytesIO(content)
    context = ParserContext(uuid.UUID(int=1), uuid.UUID(int=2), EvidenceType.FILE, source)
    return LnkParser().parse(context)


def test_lnk_parses_local_shell_link_deterministically() -> None:
    content = lnk_fixture()
    digest = hashlib.sha256(content).hexdigest()
    first = _parse(content)
    second = _parse(content)
    assert first.status is ParserExecutionStatus.COMPLETED
    assert first.model_dump() == second.model_dump()
    data = first.records[0].data
    assert data["target_path"] == "C:\\Tools\\app.exe"
    assert data["relative_path"] == ".\\app.exe"
    assert data["working_directory"] == "C:\\Tools"
    assert data["command_line_arguments"] == "--safe-test"
    assert data["creation_time"] == "2024-02-01T00:00:00+00:00"
    assert data["target_file_size"] == 12345
    assert data["target_id_list"]
    volume = data["volume_information"]
    assert isinstance(volume, dict) and volume["volume_label"] == "TESTVOL"
    tracker = data["tracker_information"]
    assert isinstance(tracker, dict) and tracker["machine_id"] == "TEST-MACHINE"
    assert hashlib.sha256(content).hexdigest() == digest


def test_lnk_preserves_network_target_without_resolving_it() -> None:
    result = _parse(lnk_fixture(network=True))
    assert result.status is ParserExecutionStatus.COMPLETED
    data = result.records[0].data
    network = data["network_information"]
    assert isinstance(network, dict)
    assert network["network_share_name"] == "\\\\SERVER\\SHARE"
    assert data["target_path"] == "\\\\SERVER\\SHARE\\folder\\target.txt"


def test_lnk_contract_and_malformed_handling() -> None:
    parser = LnkParser()
    assert parser.name == "DFIR_LNK" and parser.version == "1.0.0"
    assert parser.supported_artifact_types == frozenset({ArtifactType.LNK})
    assert _parse(b"arbitrary").status is ParserExecutionStatus.UNSUPPORTED
    malformed = bytearray(lnk_fixture())
    malformed[0:4] = (75).to_bytes(4, "little")
    assert _parse(bytes(malformed)).status is ParserExecutionStatus.FAILED


def test_lnk_partial_shell_item_produces_warning() -> None:
    malformed = bytearray(lnk_fixture())
    malformed[78:80] = (0xFFFF).to_bytes(2, "little")
    result = _parse(bytes(malformed))
    assert result.status is ParserExecutionStatus.COMPLETED_WITH_WARNINGS
    assert result.warnings
