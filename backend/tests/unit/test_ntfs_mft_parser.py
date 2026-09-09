import hashlib
import io
import uuid

from app.domain.enums import ArtifactType, EvidenceType, ParserExecutionStatus
from app.forensic.ntfs_mft import NtfsMftParser
from app.forensic.parser import ParserContext, ParserResult
from tests.support.phase6_fixtures import mft_record_fixture, ntfs_volume_fixture


def _parse(content: bytes) -> ParserResult:
    source = io.BytesIO(content)
    context = ParserContext(uuid.UUID(int=1), uuid.UUID(int=2), EvidenceType.DISK_IMAGE, source)
    return NtfsMftParser().parse(context)


def test_mft_stream_preserves_si_fn_attributes_and_fixup() -> None:
    content = mft_record_fixture()
    digest = hashlib.sha256(content).hexdigest()
    result = _parse(content)
    assert result.status is ParserExecutionStatus.COMPLETED
    record = result.records[0]
    data = record.data
    assert data["record_number"] == 42
    assert data["sequence_number"] == 5
    assert data["allocated_in_use"] is True
    assert data["directory"] is True
    standard = data["standard_information"]
    assert isinstance(standard, dict)
    assert standard["creation_time"] == "2020-01-01T00:00:00+00:00"
    file_names = data["file_names"]
    assert isinstance(file_names, list) and file_names[0]["filename"] == "example.txt"
    assert file_names[0]["creation_time"] == "2021-01-01T00:00:00+00:00"
    assert file_names[0]["parent_directory_reference"]["record_number"] == 5
    data_attributes = data["data_attributes"]
    assert isinstance(data_attributes, list)
    assert data_attributes[0]["non_resident"] is False
    assert data_attributes[1]["non_resident"] is True
    assert data_attributes[1]["data_runs"][0]["lcn"] == 5
    assert record.provenance["mft_record_number"] == 42
    assert record.provenance["source_record_offset"] == 0
    assert hashlib.sha256(content).hexdigest() == digest


def test_ntfs_volume_derives_geometry_and_locates_mft() -> None:
    result = _parse(ntfs_volume_fixture())
    assert result.status is ParserExecutionStatus.COMPLETED
    assert result.metadata["input_kind"] == "NTFS_VOLUME"
    boot = result.records[0]
    assert boot.record_type == "NTFS_VOLUME"
    assert boot.data["bytes_per_sector"] == 512
    assert boot.data["cluster_size"] == 512
    assert boot.data["mft_byte_offset"] == 512
    assert boot.data["mft_record_size"] == 1024
    assert result.records[1].provenance["source_record_offset"] == 512


def test_ntfs_is_deterministic_and_rejects_invalid_fixup_and_input() -> None:
    content = mft_record_fixture()
    assert _parse(content).model_dump() == _parse(content).model_dump()
    assert _parse(mft_record_fixture(valid_fixup=False)).status is ParserExecutionStatus.FAILED
    assert _parse(b"arbitrary").status is ParserExecutionStatus.UNSUPPORTED


def test_ntfs_contract() -> None:
    parser = NtfsMftParser()
    assert parser.name == "DFIR_NTFS_MFT" and parser.version == "1.0.0"
    assert parser.supported_artifact_types == frozenset({ArtifactType.NTFS_MFT})
