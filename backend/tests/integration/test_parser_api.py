import hashlib
import os
import uuid
from collections.abc import Generator
from pathlib import Path
from typing import cast

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from alembic import command
from app.db.models import Artifact, ArtifactRecord, AuditEvent, Evidence, EvidenceHash
from app.db.session import get_db
from app.forensic.registry import ParserRegistry
from app.main import app
from app.services.evidence_service import evidence_service
from app.services.evidence_storage import EvidenceStorage
from app.services.parser_execution_service import parser_execution_service
from tests.support.reference_parser import ReferenceParser

CONTENT = b"synthetic parser framework bytes"


def _test_database_url() -> str:
    database_url = os.getenv("TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration tests")
    if "test" not in (make_url(database_url).database or "").lower():
        pytest.fail("TEST_DATABASE_URL must identify a database whose name contains 'test'")
    return database_url


@pytest.fixture(scope="module")
def parser_engine() -> Generator[Engine, None, None]:
    database_url = _test_database_url()
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    command.upgrade(config, "head")
    engine = create_engine(database_url, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture
def parser_session(parser_engine: Engine) -> Generator[Session, None, None]:
    with parser_engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            yield session
        transaction.rollback()


@pytest.fixture
def client(
    parser_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[TestClient, None, None]:
    def override_database() -> Generator[Session, None, None]:
        yield parser_session

    storage = EvidenceStorage(tmp_path / "evidence")
    monkeypatch.setattr(evidence_service, "storage", storage)
    monkeypatch.setattr(parser_execution_service, "storage", storage)
    monkeypatch.setattr(parser_execution_service, "registry", ParserRegistry([ReferenceParser()]))
    app.dependency_overrides[get_db] = override_database
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _registered_evidence(client: TestClient) -> dict[str, object]:
    case_response = client.post("/api/cases", json={"name": "Synthetic parser API case"})
    assert case_response.status_code == 201
    response = client.post(
        f"/api/cases/{case_response.json()['id']}/evidence",
        files={"file": ("synthetic.bin", CONTENT, "application/octet-stream")},
        data={"evidence_type": "FILE", "custody_person": "Test Custodian"},
    )
    assert response.status_code == 201
    return cast(dict[str, object], response.json())


def _parse(client: TestClient, evidence_id: object) -> dict[str, object]:
    response = client.post(
        f"/api/evidence/{evidence_id}/parse", json={"artifact_type": "REFERENCE"}
    )
    assert response.status_code == 200, response.text
    return cast(dict[str, object], response.json())


def test_execution_persists_provenance_audit_and_preserves_evidence(
    client: TestClient, parser_session: Session
) -> None:
    evidence_data = _registered_evidence(client)
    evidence_id = uuid.UUID(str(evidence_data["id"]))
    evidence = parser_session.get(Evidence, evidence_id)
    assert evidence is not None and evidence.stored_path is not None
    source = parser_execution_service.storage.resolve_for_read(evidence.stored_path)
    bytes_before = source.read_bytes()
    acquisition_before = parser_session.scalar(
        select(EvidenceHash.digest).where(
            EvidenceHash.evidence_id == evidence_id, EvidenceHash.purpose == "ACQUISITION"
        )
    )

    result = _parse(client, evidence_id)
    artifact_id = uuid.UUID(str(result["id"]))
    assert result["status"] == "COMPLETED"
    assert result["record_count"] == 3
    assert result["parser_name"] == "TEST_REFERENCE_PARSER"
    assert source.read_bytes() == bytes_before == CONTENT
    acquisition_after = parser_session.scalar(
        select(EvidenceHash.digest).where(
            EvidenceHash.evidence_id == evidence_id, EvidenceHash.purpose == "ACQUISITION"
        )
    )
    assert acquisition_before == acquisition_after == hashlib.sha256(CONTENT).hexdigest()

    artifact = parser_session.get(Artifact, artifact_id)
    record = parser_session.scalar(
        select(ArtifactRecord).where(ArtifactRecord.artifact_id == artifact_id)
    )
    assert artifact is not None and artifact.evidence_id == evidence_id
    assert record is not None and record.artifact_id == artifact.id
    audit = parser_session.scalar(
        select(AuditEvent).where(
            AuditEvent.evidence_id == evidence_id, AuditEvent.action == "PARSER_EXECUTED"
        )
    )
    assert audit is not None and audit.details is not None
    assert audit.details["record_count"] == 3


def test_record_ordering_pagination_and_reparsing_history(client: TestClient) -> None:
    evidence = _registered_evidence(client)
    first = _parse(client, evidence["id"])
    page_one = client.get(f"/api/artifacts/{first['id']}/records", params={"limit": 2})
    page_two = client.get(f"/api/artifacts/{first['id']}/records", params={"limit": 2, "offset": 2})
    assert page_one.status_code == 200 and page_two.status_code == 200
    assert [item["source_record_identifier"] for item in page_one.json()["data"]] == [
        "earlier",
        "later",
    ]
    assert page_two.json()["data"][0]["source_record_identifier"] == "undated"

    parser_execution_service.registry = ParserRegistry([ReferenceParser(version="test-2")])
    second = _parse(client, evidence["id"])
    assert first["id"] != second["id"]
    listing = client.get(f"/api/evidence/{evidence['id']}/artifacts")
    assert listing.status_code == 200 and listing.json()["meta"]["total"] == 2
    versions = {item["parser_version"] for item in listing.json()["data"]}
    assert versions == {"test-1", "test-2"}
    assert client.get(f"/api/artifacts/{first['id']}").status_code == 200
    assert client.get(f"/api/artifacts/{first['id']}/records").json()["meta"]["total"] == 3


@pytest.mark.parametrize(
    ("mode", "expected_status", "warning_count", "error_count"),
    [
        ("warning", "COMPLETED_WITH_WARNINGS", 1, 0),
        ("failure", "FAILED", 0, 1),
        ("unsupported", "UNSUPPORTED", 0, 1),
        ("exception", "FAILED", 0, 1),
        ("malformed", "FAILED", 0, 1),
    ],
)
def test_warning_failure_exception_and_malformed_results(
    client: TestClient,
    parser_session: Session,
    mode: str,
    expected_status: str,
    warning_count: int,
    error_count: int,
) -> None:
    evidence = _registered_evidence(client)
    parser_execution_service.registry = ParserRegistry([ReferenceParser(mode=mode)])
    result = _parse(client, evidence["id"])
    assert result["status"] == expected_status
    assert len(cast(list[object], result["warnings"])) == warning_count
    assert len(cast(list[object], result["errors"])) == error_count
    audit = parser_session.scalar(
        select(AuditEvent).where(
            AuditEvent.evidence_id == uuid.UUID(str(evidence["id"])),
            AuditEvent.action == "PARSER_EXECUTED",
        )
    )
    assert audit is not None and audit.details is not None
    assert audit.details["warning_count"] == warning_count
    assert audit.details["error_count"] == error_count


def test_api_rejects_unsupported_paths_and_missing_resources(client: TestClient) -> None:
    evidence = _registered_evidence(client)
    unsupported = client.post(
        f"/api/evidence/{evidence['id']}/parse", json={"artifact_type": "EVTX"}
    )
    assert unsupported.status_code == 422
    for value in ("../escape", "C:\\absolute", "/absolute"):
        response = client.post(
            f"/api/evidence/{evidence['id']}/parse",
            json={"artifact_type": "REFERENCE", "path": value},
        )
        assert response.status_code == 422
    missing = uuid.uuid4()
    assert (
        client.post(
            f"/api/evidence/{missing}/parse", json={"artifact_type": "REFERENCE"}
        ).status_code
        == 404
    )
    assert client.get(f"/api/evidence/{missing}/artifacts").status_code == 404
    assert client.get(f"/api/artifacts/{missing}").status_code == 404
    assert client.get(f"/api/artifacts/{missing}/records").status_code == 404
