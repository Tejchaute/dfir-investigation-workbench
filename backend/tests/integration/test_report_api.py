import hashlib
import json
import os
import uuid
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from alembic import command
from app.core.config import get_settings
from app.db.models import (
    Artifact,
    ArtifactRecord,
    AuditEvent,
    Case,
    ChainOfCustodyEntry,
    CorrelationMatch,
    CorrelationMatchEvent,
    CorrelationRun,
    Evidence,
    EvidenceHash,
    Finding,
    Report,
    TimelineEvent,
)
from app.db.session import get_db
from app.domain.enums import (
    ArtifactType,
    CaseStatus,
    CorrelationRunStatus,
    EvidenceType,
    FindingConfidence,
    FindingSeverity,
    FindingStatus,
    FindingType,
    ParserExecutionStatus,
    TimelineEventType,
    TimestampPrecision,
)
from app.main import app

CASE_ID = uuid.UUID(int=9000)
EVIDENCE_ID = uuid.UUID(int=9001)
TIME = datetime(2026, 3, 1, 12, tzinfo=UTC)


def _database_url() -> str:
    value = os.getenv("TEST_DATABASE_URL")
    if value is None:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration tests")
    if "test" not in (make_url(value).database or "").lower():
        pytest.fail("TEST_DATABASE_URL must identify a test database")
    return value


@pytest.fixture(scope="module")
def report_engine() -> Generator[Engine, None, None]:
    url = _database_url()
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    command.upgrade(config, "head")
    engine = create_engine(url)
    yield engine
    engine.dispose()


@pytest.fixture
def report_session(report_engine: Engine) -> Generator[Session, None, None]:
    with report_engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            yield session
        transaction.rollback()


@pytest.fixture
def report_client(
    report_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Generator[TestClient, None, None]:
    monkeypatch.setenv("REPORT_ROOT", str(tmp_path / "exports"))
    monkeypatch.setenv("EVIDENCE_ROOT", str(tmp_path / "evidence"))
    get_settings.cache_clear()

    def override() -> Generator[Session, None, None]:
        yield report_session

    app.dependency_overrides[get_db] = override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def _seed(session: Session) -> dict[str, object]:
    case = Case(
        id=CASE_ID,
        case_number="CASE-REPORT-0001",
        name="Synthetic report case",
        status=CaseStatus.OPEN,
    )
    evidence = Evidence(
        id=EVIDENCE_ID,
        case_id=CASE_ID,
        evidence_number="EVD-REPORT-0001",
        name="synthetic.evtx",
        evidence_type=EvidenceType.LOG_FILE,
        size_bytes=10,
    )
    acquisition = EvidenceHash(
        id=uuid.UUID(int=9002),
        evidence_id=EVIDENCE_ID,
        algorithm="SHA256",
        digest="a" * 64,
        computed_at=TIME,
        purpose="ACQUISITION",
    )
    verification = EvidenceHash(
        id=uuid.UUID(int=9003),
        evidence_id=EVIDENCE_ID,
        algorithm="SHA256",
        digest="a" * 64,
        computed_at=TIME,
        purpose="VERIFICATION",
    )
    custody = ChainOfCustodyEntry(
        id=uuid.UUID(int=9004),
        evidence_id=EVIDENCE_ID,
        timestamp=TIME,
        person="Test Custodian",
        action="REGISTERED",
    )
    session.add_all([case, evidence, acquisition, verification, custody])
    session.flush()
    artifact = Artifact(
        id=uuid.UUID(int=9010),
        evidence_id=EVIDENCE_ID,
        artifact_type=ArtifactType.EVTX,
        parser_name="DFIR_EVTX",
        parser_version="1.0.0",
        status=ParserExecutionStatus.COMPLETED,
        metadata_={},
        warnings=[],
        errors=[],
        statistics={},
    )
    record = ArtifactRecord(
        id=uuid.UUID(int=9011),
        artifact_id=artifact.id,
        record_type="EVTX_EVENT",
        source_record_identifier="1",
        event_time=TIME,
        data={"event_id": 4688},
        provenance={"evidence_id": str(EVIDENCE_ID)},
    )
    event = TimelineEvent(
        id=uuid.UUID(int=9012),
        case_id=CASE_ID,
        evidence_id=EVIDENCE_ID,
        artifact_id=artifact.id,
        artifact_record_id=record.id,
        parser_name="DFIR_EVTX",
        parser_version="1.0.0",
        artifact_type=ArtifactType.EVTX,
        event_type=TimelineEventType.EVTX_EVENT,
        event_time=TIME,
        raw_time="134000000000000000",
        time_source="evtx.system_time",
        time_semantics="Source event timestamp",
        timestamp_precision=TimestampPrecision.MICROSECOND,
        event_ordinal=0,
        description="Windows event 4688 observed from Security",
        source_identifier="1",
        metadata_={"event_id": 4688, "channel": "Security"},
        provenance={"artifact_record_id": str(record.id)},
    )
    run = CorrelationRun(
        id=uuid.UUID(int=9013),
        case_id=CASE_ID,
        started_at=TIME,
        completed_at=TIME,
        status=CorrelationRunStatus.COMPLETED,
        rule_set_version="1.0.0",
        temporal_window_seconds=300,
        event_count=1,
        matched_count=1,
        finding_count=1,
        rules_evaluated=[{"rule_id": "TEST-RULE", "rule_version": "1.0.0"}],
        warnings=[],
        errors=[],
    )
    session.add_all([artifact, record, event, run])
    session.flush()
    match = CorrelationMatch(
        id=uuid.UUID(int=9014),
        correlation_run_id=run.id,
        case_id=CASE_ID,
        rule_id="TEST-RULE",
        rule_version="1.0.0",
        deterministic_key="b" * 64,
        temporal_delta_seconds=0,
        match_basis="exact_path_match",
        explanation="Deterministic test association; no causality is established.",
        metadata_={},
    )
    session.add(match)
    session.flush()
    link = CorrelationMatchEvent(
        correlation_match_id=match.id,
        timeline_event_id=event.id,
        event_role="observation",
        event_order=0,
    )
    finding = Finding(
        correlation_run_id=run.id,
        correlation_match_id=match.id,
        case_id=CASE_ID,
        finding_type=FindingType.PROCESS_EXECUTION_CORROBORATED,
        title="Evidence-backed test finding",
        description="Observation and deterministic correlation only; examiner review is required.",
        status=FindingStatus.OPEN,
        severity=FindingSeverity.MEDIUM,
        confidence=FindingConfidence.MEDIUM,
        rule_id="TEST-RULE",
        rule_version="1.0.0",
        deterministic_key="c" * 64,
        metadata_={},
    )
    audit = AuditEvent(
        case_id=CASE_ID,
        evidence_id=EVIDENCE_ID,
        action="EVIDENCE_REGISTERED",
        actor="LOCAL_APPLICATION",
        timestamp=TIME,
        details={"bounded": True},
    )
    session.add_all([link, finding, audit])
    session.commit()
    return {
        "evidence": evidence,
        "record": record,
        "event": event,
        "match": match,
        "finding": finding,
    }


@pytest.mark.parametrize(
    ("format_name", "content_type", "prefix"),
    [
        ("json", "application/json", b"{"),
        ("html", "text/html", b"<!doctype html>"),
        ("pdf", "application/pdf", b"%PDF-"),
    ],
)
def test_report_api_generates_lists_downloads_and_preserves_sources(
    report_client: TestClient,
    report_session: Session,
    format_name: str,
    content_type: str,
    prefix: bytes,
) -> None:
    seeded = _seed(report_session)
    record = cast(ArtifactRecord, seeded["record"])
    event = cast(TimelineEvent, seeded["event"])
    match = cast(CorrelationMatch, seeded["match"])
    finding = cast(Finding, seeded["finding"])
    snapshots = {
        "hashes": list(report_session.scalars(select(EvidenceHash.digest))),
        "custody": report_session.scalar(select(func.count()).select_from(ChainOfCustodyEntry)),
        "record": dict(record.data),
        "event": dict(event.metadata_),
        "match": dict(match.metadata_),
        "finding": finding.description,
    }
    response = report_client.post(f"/api/cases/{CASE_ID}/reports", json={"format": format_name})
    assert response.status_code == 201, response.text
    report_id = response.json()["id"]
    assert response.json()["status"] == "GENERATED"
    assert len(response.json()["artifacts"]) == 1
    listing = report_client.get(f"/api/cases/{CASE_ID}/reports")
    assert listing.status_code == 200 and listing.json()["meta"]["total"] == 1
    assert report_client.get(f"/api/reports/{report_id}").status_code == 200
    download = report_client.get(f"/api/reports/{report_id}/download")
    assert download.status_code == 200
    assert download.headers["content-type"].startswith(content_type)
    assert download.content.startswith(prefix)
    assert (
        hashlib.sha256(download.content).hexdigest()
        == response.json()["artifacts"][0]["content_hash"]
    )
    report = report_session.get(Report, uuid.UUID(report_id))
    assert report is not None
    assert (
        report.content_hash
        == hashlib.sha256(
            Path(get_settings().report_root, report.snapshot_path).read_bytes()
        ).hexdigest()
    )
    assert (
        report_session.scalar(
            select(func.count())
            .select_from(AuditEvent)
            .where(AuditEvent.action == "REPORT_GENERATED")
        )
        == 1
    )
    assert list(report_session.scalars(select(EvidenceHash.digest))) == snapshots["hashes"]
    assert (
        report_session.scalar(select(func.count()).select_from(ChainOfCustodyEntry))
        == snapshots["custody"]
    )
    assert record.data == snapshots["record"]
    assert event.metadata_ == snapshots["event"]
    assert match.metadata_ == snapshots["match"]
    assert finding.description == snapshots["finding"]
    if format_name == "json":
        payload = json.loads(download.content)
        assert list(payload) == sorted(payload)
        assert payload["evidence_integrity"][0]["verification_status"] == "MATCH"
        assert payload["findings"][0]["timeline_event_ids"] == [str(uuid.UUID(int=9012))]
        assert any(item["action"] == "REPORT_GENERATED" for item in payload["audit_summary"])


def test_report_api_rejects_invalid_and_missing_resources(
    report_client: TestClient, report_session: Session
) -> None:
    _seed(report_session)
    assert (
        report_client.post(f"/api/cases/{CASE_ID}/reports", json={"format": "docx"}).status_code
        == 422
    )
    missing = uuid.uuid4()
    assert (
        report_client.post(f"/api/cases/{missing}/reports", json={"format": "json"}).status_code
        == 404
    )
    assert report_client.get(f"/api/reports/{missing}").status_code == 404
    assert report_client.get(f"/api/reports/{missing}/download").status_code == 404
