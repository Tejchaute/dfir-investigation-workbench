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
from app.main import app
from app.services.evidence_service import evidence_service
from app.services.evidence_storage import EvidenceStorage
from app.services.parser_execution_service import parser_execution_service
from tests.support.phase5_fixtures import materialize_fixture


def _test_database_url() -> str:
    database_url = os.getenv("TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration tests")
    if "test" not in (make_url(database_url).database or "").lower():
        pytest.fail("TEST_DATABASE_URL must identify a database whose name contains 'test'")
    return database_url


@pytest.fixture(scope="module")
def phase5_engine() -> Generator[Engine, None, None]:
    database_url = _test_database_url()
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    command.upgrade(config, "head")
    engine = create_engine(database_url, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture
def phase5_session(phase5_engine: Engine) -> Generator[Session, None, None]:
    with phase5_engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            yield session
        transaction.rollback()


@pytest.fixture
def phase5_client(
    phase5_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[TestClient, None, None]:
    def override_database() -> Generator[Session, None, None]:
        yield phase5_session

    storage = EvidenceStorage(tmp_path / "evidence")
    monkeypatch.setattr(evidence_service, "storage", storage)
    monkeypatch.setattr(parser_execution_service, "storage", storage)
    app.dependency_overrides[get_db] = override_database
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def _register_fixture(
    client: TestClient,
    tmp_path: Path,
    fixture_name: str,
    filename: str,
    evidence_type: str,
) -> tuple[dict[str, object], bytes]:
    fixture_path = tmp_path / filename
    content = materialize_fixture(fixture_name, fixture_path)
    case = client.post("/api/cases", json={"name": f"Synthetic {evidence_type} parser case"})
    assert case.status_code == 201
    response = client.post(
        f"/api/cases/{case.json()['id']}/evidence",
        files={"file": (filename, content, "application/octet-stream")},
        data={"evidence_type": evidence_type, "custody_person": "Test Custodian"},
    )
    assert response.status_code == 201, response.text
    return cast(dict[str, object], response.json()), content


@pytest.mark.parametrize(
    ("fixture_name", "filename", "evidence_type", "artifact_type", "parser_name"),
    [
        ("evtx_issue38.evtx.gz.b64", "events.evtx", "LOG_FILE", "EVTX", "DFIR_EVTX"),
        (
            "registry_issue22.hive.gz.b64",
            "offline.hive",
            "REGISTRY_HIVE",
            "REGISTRY",
            "DFIR_REGISTRY",
        ),
    ],
)
def test_real_parser_api_flow_preserves_integrity_provenance_and_history(
    phase5_client: TestClient,
    phase5_session: Session,
    tmp_path: Path,
    fixture_name: str,
    filename: str,
    evidence_type: str,
    artifact_type: str,
    parser_name: str,
) -> None:
    evidence_data, content = _register_fixture(
        phase5_client, tmp_path, fixture_name, filename, evidence_type
    )
    evidence_id = uuid.UUID(str(evidence_data["id"]))
    evidence = phase5_session.get(Evidence, evidence_id)
    assert evidence is not None and evidence.stored_path is not None
    controlled_source = parser_execution_service.storage.resolve_for_read(evidence.stored_path)
    digest_before = hashlib.sha256(controlled_source.read_bytes()).hexdigest()
    acquisition_before = phase5_session.scalar(
        select(EvidenceHash.digest).where(
            EvidenceHash.evidence_id == evidence_id,
            EvidenceHash.purpose == "ACQUISITION",
        )
    )

    first = phase5_client.post(
        f"/api/evidence/{evidence_id}/parse", json={"artifact_type": artifact_type}
    )
    second = phase5_client.post(
        f"/api/evidence/{evidence_id}/parse", json={"artifact_type": artifact_type}
    )
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["id"] != second.json()["id"]
    assert first.json()["parser_name"] == parser_name
    assert first.json()["parser_version"] == "1.0.0"
    assert first.json()["record_count"] > 0

    listing = phase5_client.get(f"/api/evidence/{evidence_id}/artifacts")
    assert listing.status_code == 200 and listing.json()["meta"]["total"] == 2
    artifact_id = uuid.UUID(first.json()["id"])
    artifact = phase5_session.get(Artifact, artifact_id)
    record = phase5_session.scalar(
        select(ArtifactRecord).where(ArtifactRecord.artifact_id == artifact_id)
    )
    assert artifact is not None and artifact.evidence_id == evidence_id
    assert record is not None and record.artifact_id == artifact.id
    assert record.provenance["evidence_id"] == str(evidence_id)
    audits = list(
        phase5_session.scalars(
            select(AuditEvent).where(
                AuditEvent.evidence_id == evidence_id,
                AuditEvent.action == "PARSER_EXECUTED",
            )
        )
    )
    assert len(audits) == 2
    assert all(event.details and event.details["parser_name"] == parser_name for event in audits)

    records_first = phase5_client.get(
        f"/api/artifacts/{artifact_id}/records", params={"limit": 100}
    ).json()["data"]
    records_second = phase5_client.get(
        f"/api/artifacts/{artifact_id}/records", params={"limit": 100}
    ).json()["data"]
    assert [record["id"] for record in records_first] == [record["id"] for record in records_second]
    assert phase5_client.get(f"/api/artifacts/{artifact_id}").status_code == 200

    acquisition_after = phase5_session.scalar(
        select(EvidenceHash.digest).where(
            EvidenceHash.evidence_id == evidence_id,
            EvidenceHash.purpose == "ACQUISITION",
        )
    )
    assert controlled_source.read_bytes() == content
    assert hashlib.sha256(controlled_source.read_bytes()).hexdigest() == digest_before
    assert acquisition_before == acquisition_after == hashlib.sha256(content).hexdigest()


@pytest.mark.parametrize(
    ("content", "artifact_type", "expected_status"),
    [
        (b"ElfFile\x00broken", "EVTX", "FAILED"),
        (b"regfbroken", "REGISTRY", "FAILED"),
        (b"wrong format", "EVTX", "UNSUPPORTED"),
        (b"wrong format", "REGISTRY", "UNSUPPORTED"),
    ],
)
def test_real_parser_api_preserves_failed_and_unsupported_results(
    phase5_client: TestClient,
    tmp_path: Path,
    content: bytes,
    artifact_type: str,
    expected_status: str,
) -> None:
    source = tmp_path / f"{artifact_type}.bin"
    source.write_bytes(content)
    case = phase5_client.post("/api/cases", json={"name": "Synthetic malformed input"})
    evidence = phase5_client.post(
        f"/api/cases/{case.json()['id']}/evidence",
        files={"file": (source.name, content, "application/octet-stream")},
        data={"evidence_type": "FILE", "custody_person": "Test Custodian"},
    )
    response = phase5_client.post(
        f"/api/evidence/{evidence.json()['id']}/parse",
        json={"artifact_type": artifact_type},
    )
    assert response.status_code == 200
    assert response.json()["status"] == expected_status
    assert response.json()["record_count"] == 0
    assert response.json()["errors"]
