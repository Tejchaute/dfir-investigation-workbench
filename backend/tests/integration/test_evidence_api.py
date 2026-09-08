import hashlib
import os
import re
import uuid
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from alembic import command
from app.db.models import AuditEvent, Evidence, EvidenceHash
from app.db.session import get_db
from app.main import app
from app.services.evidence_service import evidence_service
from app.services.evidence_storage import EvidenceStorage


def _test_database_url() -> str:
    database_url = os.getenv("TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration tests")
    if "test" not in (make_url(database_url).database or "").lower():
        pytest.fail("TEST_DATABASE_URL must identify a database whose name contains 'test'")
    return database_url


@pytest.fixture(scope="module")
def evidence_engine() -> Generator[Engine, None, None]:
    database_url = _test_database_url()
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    command.upgrade(config, "head")
    engine = create_engine(database_url, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture
def evidence_session(evidence_engine: Engine) -> Generator[Session, None, None]:
    with evidence_engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            yield session
        transaction.rollback()


@pytest.fixture
def client(
    evidence_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[TestClient, None, None]:
    def override_database() -> Generator[Session, None, None]:
        yield evidence_session

    monkeypatch.setattr(evidence_service, "storage", EvidenceStorage(tmp_path / "evidence"))
    app.dependency_overrides[get_db] = override_database
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _create_case(client: TestClient) -> dict[str, object]:
    response = client.post("/api/cases", json={"name": "Synthetic evidence API case"})
    assert response.status_code == 201
    return cast(dict[str, object], response.json())


def _register(
    client: TestClient, case_id: str, filename: str = "synthetic.bin"
) -> dict[str, object]:
    response = client.post(
        f"/api/cases/{case_id}/evidence",
        files={"file": (filename, b"synthetic isolated test bytes", "application/octet-stream")},
        data={
            "evidence_type": "FILE",
            "description": "Test-only metadata",
            "collected_by": "Test Collector",
            "collected_at": datetime.now(UTC).isoformat(),
            "custody_person": "Test Custodian",
            "custody_location": "Test fixture",
            "custody_notes": "Synthetic test record",
        },
    )
    assert response.status_code == 201, response.text
    return cast(dict[str, object], response.json())


def test_registration_persists_hash_custody_and_audit(
    client: TestClient, evidence_session: Session
) -> None:
    case = _create_case(client)
    item = _register(client, str(case["id"]))
    assert re.fullmatch(rf"EVD-{datetime.now(UTC).year}-\d{{4,}}", str(item["evidence_number"]))
    assert item["size_bytes"] == len(b"synthetic isolated test bytes")
    assert "stored_path" not in item and "original_path" not in item
    evidence_id = uuid.UUID(str(item["id"]))
    acquisition = evidence_session.scalar(
        select(EvidenceHash).where(
            EvidenceHash.evidence_id == evidence_id, EvidenceHash.purpose == "ACQUISITION"
        )
    )
    assert acquisition is not None
    assert acquisition.digest == hashlib.sha256(b"synthetic isolated test bytes").hexdigest()
    audit = evidence_session.scalar(
        select(AuditEvent).where(
            AuditEvent.evidence_id == evidence_id, AuditEvent.action == "EVIDENCE_REGISTERED"
        )
    )
    assert audit is not None
    custody = client.get(f"/api/evidence/{evidence_id}/coc")
    assert custody.status_code == 200
    assert custody.json()[0]["person"] == "Test Custodian"


def test_list_get_hashes_and_verification(client: TestClient, evidence_session: Session) -> None:
    case = _create_case(client)
    item = _register(client, str(case["id"]))
    evidence_id = str(item["id"])
    listing = client.get(f"/api/cases/{case['id']}/evidence", params={"limit": 1})
    assert listing.status_code == 200 and listing.json()["meta"]["total"] == 1
    assert "stored_path" not in listing.json()["data"][0]
    assert client.get(f"/api/cases/{case['id']}/evidence", params={"limit": 101}).status_code == 422
    assert client.get(f"/api/evidence/{evidence_id}").status_code == 200
    assert client.get(f"/api/evidence/{evidence_id}/hashes").json()[0]["purpose"] == "ACQUISITION"

    verified = client.post(f"/api/evidence/{evidence_id}/verify")
    assert verified.status_code == 200 and verified.json()["match"] is True
    hashes = client.get(f"/api/evidence/{evidence_id}/hashes").json()
    assert [record["purpose"] for record in hashes] == ["ACQUISITION", "VERIFICATION"]
    audit = evidence_session.scalar(
        select(AuditEvent).where(
            AuditEvent.evidence_id == uuid.UUID(evidence_id),
            AuditEvent.action == "EVIDENCE_VERIFIED",
        )
    )
    assert audit is not None and audit.details is not None and audit.details["match"] is True


def test_integrity_mismatch_does_not_replace_acquisition(
    client: TestClient, evidence_session: Session
) -> None:
    case = _create_case(client)
    item = _register(client, str(case["id"]))
    evidence_id = uuid.UUID(str(item["id"]))
    evidence = evidence_session.get(Evidence, evidence_id)
    assert evidence is not None and evidence.stored_path is not None
    evidence_service.storage.resolve_for_read(evidence.stored_path).write_bytes(
        b"synthetic external alteration"
    )
    response = client.post(f"/api/evidence/{evidence_id}/verify")
    assert response.status_code == 200 and response.json()["match"] is False
    hashes = client.get(f"/api/evidence/{evidence_id}/hashes").json()
    assert hashes[0]["purpose"] == "ACQUISITION"
    assert hashes[-1]["purpose"] == "VERIFICATION"


def test_restrictions_and_missing_resources(client: TestClient) -> None:
    case = _create_case(client)
    assert client.post(f"/api/cases/{case['id']}/close").status_code == 200
    blocked = client.post(
        f"/api/cases/{case['id']}/evidence",
        files={"file": ("synthetic.bin", b"bytes")},
        data={"evidence_type": "FILE", "custody_person": "Test Custodian"},
    )
    assert blocked.status_code == 409
    open_case = _create_case(client)
    unsafe = client.post(
        f"/api/cases/{open_case['id']}/evidence",
        files={"file": ("../escape.bin", b"bytes")},
        data={"evidence_type": "FILE", "custody_person": "Test Custodian"},
    )
    assert unsafe.status_code == 400
    missing = uuid.uuid4()
    assert client.get(f"/api/cases/{missing}/evidence").status_code == 404
    assert client.get(f"/api/evidence/{missing}").status_code == 404
    assert client.get(f"/api/evidence/{missing}/hashes").status_code == 404
    assert client.get(f"/api/evidence/{missing}/coc").status_code == 404
    assert client.post(f"/api/evidence/{missing}/verify").status_code == 404
