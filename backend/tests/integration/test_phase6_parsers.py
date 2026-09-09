import hashlib
import os
import uuid
from collections.abc import Generator
from pathlib import Path
from typing import cast

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from alembic import command
from app.db.models import (
    Artifact,
    ArtifactRecord,
    AuditEvent,
    ChainOfCustodyEntry,
    Evidence,
    EvidenceHash,
)
from app.db.session import get_db
from app.domain.enums import ArtifactType
from app.forensic.registry import parser_registry
from app.main import app
from app.services.evidence_service import evidence_service
from app.services.evidence_storage import EvidenceStorage
from app.services.parser_execution_service import parser_execution_service
from tests.support.phase6_fixtures import lnk_fixture, mft_record_fixture, prefetch_fixture


def _test_database_url() -> str:
    database_url = os.getenv("TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration tests")
    if "test" not in (make_url(database_url).database or "").lower():
        pytest.fail("TEST_DATABASE_URL must identify a database whose name contains 'test'")
    return database_url


@pytest.fixture(scope="module")
def phase6_engine() -> Generator[Engine, None, None]:
    database_url = _test_database_url()
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    command.upgrade(config, "head")
    engine = create_engine(database_url, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture
def phase6_session(phase6_engine: Engine) -> Generator[Session, None, None]:
    with phase6_engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            yield session
        transaction.rollback()


@pytest.fixture
def phase6_client(
    phase6_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[TestClient, None, None]:
    def override_database() -> Generator[Session, None, None]:
        yield phase6_session

    storage = EvidenceStorage(tmp_path / "evidence")
    monkeypatch.setattr(evidence_service, "storage", storage)
    monkeypatch.setattr(parser_execution_service, "storage", storage)
    monkeypatch.setattr(parser_execution_service, "registry", parser_registry)
    app.dependency_overrides[get_db] = override_database
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.parametrize(
    ("content", "filename", "evidence_type", "artifact_type", "parser_name"),
    [
        (prefetch_fixture(), "APP.EXE-1234ABCD.pf", "FILE", "PREFETCH", "DFIR_PREFETCH"),
        (lnk_fixture(), "application.lnk", "FILE", "LNK", "DFIR_LNK"),
        (
            mft_record_fixture(),
            "$MFT",
            "DISK_IMAGE",
            "NTFS_MFT",
            "DFIR_NTFS_MFT",
        ),
    ],
)
def test_phase6_api_persistence_reparse_provenance_and_integrity(
    phase6_client: TestClient,
    phase6_session: Session,
    content: bytes,
    filename: str,
    evidence_type: str,
    artifact_type: str,
    parser_name: str,
) -> None:
    case = phase6_client.post("/api/cases", json={"name": "Synthetic Phase 6 parser case"})
    evidence_response = phase6_client.post(
        f"/api/cases/{case.json()['id']}/evidence",
        files={"file": (filename, content, "application/octet-stream")},
        data={"evidence_type": evidence_type, "custody_person": "Test Custodian"},
    )
    assert evidence_response.status_code == 201
    evidence_data = cast(dict[str, object], evidence_response.json())
    evidence_id = uuid.UUID(str(evidence_data["id"]))
    evidence = phase6_session.get(Evidence, evidence_id)
    assert evidence is not None and evidence.stored_path is not None
    source = parser_execution_service.storage.resolve_for_read(evidence.stored_path)
    source_before = source.read_bytes()
    hash_before = phase6_session.scalar(
        select(EvidenceHash.digest).where(
            EvidenceHash.evidence_id == evidence_id,
            EvidenceHash.purpose == "ACQUISITION",
        )
    )
    custody_before = phase6_session.scalar(
        select(func.count())
        .select_from(ChainOfCustodyEntry)
        .where(ChainOfCustodyEntry.evidence_id == evidence_id)
    )

    first = phase6_client.post(
        f"/api/evidence/{evidence_id}/parse", json={"artifact_type": artifact_type}
    )
    second = phase6_client.post(
        f"/api/evidence/{evidence_id}/parse", json={"artifact_type": artifact_type}
    )
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["status"] == "COMPLETED"
    assert first.json()["parser_name"] == parser_name
    assert first.json()["parser_version"] == "1.0.0"
    assert first.json()["id"] != second.json()["id"]
    artifact_id = uuid.UUID(first.json()["id"])
    artifact = phase6_session.get(Artifact, artifact_id)
    records = list(
        phase6_session.scalars(
            select(ArtifactRecord).where(ArtifactRecord.artifact_id == artifact_id)
        )
    )
    assert artifact is not None and artifact.evidence_id == evidence_id
    assert records and all(
        record.provenance["evidence_id"] == str(evidence_id) for record in records
    )
    audits = list(
        phase6_session.scalars(
            select(AuditEvent).where(
                AuditEvent.evidence_id == evidence_id,
                AuditEvent.action == "PARSER_EXECUTED",
            )
        )
    )
    assert len(audits) == 2
    assert all(event.details and event.details["parser_name"] == parser_name for event in audits)
    listing = phase6_client.get(f"/api/evidence/{evidence_id}/artifacts")
    assert listing.json()["meta"]["total"] == 2
    first_order = phase6_client.get(f"/api/artifacts/{artifact_id}/records").json()["data"]
    second_order = phase6_client.get(f"/api/artifacts/{artifact_id}/records").json()["data"]
    assert [item["id"] for item in first_order] == [item["id"] for item in second_order]

    hash_after = phase6_session.scalar(
        select(EvidenceHash.digest).where(
            EvidenceHash.evidence_id == evidence_id,
            EvidenceHash.purpose == "ACQUISITION",
        )
    )
    custody_after = phase6_session.scalar(
        select(func.count())
        .select_from(ChainOfCustodyEntry)
        .where(ChainOfCustodyEntry.evidence_id == evidence_id)
    )
    assert source.read_bytes() == source_before == content
    assert hash_before == hash_after == hashlib.sha256(content).hexdigest()
    assert custody_before == custody_after == 1


def test_phase6_production_registry_is_explicit_and_complete() -> None:
    assert parser_registry.get(ArtifactType.PREFETCH).name == "DFIR_PREFETCH"
    assert parser_registry.get(ArtifactType.LNK).name == "DFIR_LNK"
    assert parser_registry.get(ArtifactType.NTFS_MFT).name == "DFIR_NTFS_MFT"
