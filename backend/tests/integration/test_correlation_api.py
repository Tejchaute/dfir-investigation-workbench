import os
import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
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
    Case,
    ChainOfCustodyEntry,
    CorrelationMatch,
    CorrelationMatchEvent,
    CorrelationRun,
    Evidence,
    EvidenceHash,
    Finding,
    TimelineEvent,
)
from app.db.session import get_db
from app.domain.enums import (
    ArtifactType,
    CaseStatus,
    EvidenceType,
    ParserExecutionStatus,
    TimelineEventType,
    TimestampPrecision,
)
from app.main import app

CASE_ID = uuid.UUID(int=5000)
EVIDENCE_ID = uuid.UUID(int=5001)
BASE_TIME = datetime(2026, 2, 1, 12, tzinfo=UTC)


def _test_database_url() -> str:
    database_url = os.getenv("TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration tests")
    if "test" not in (make_url(database_url).database or "").lower():
        pytest.fail("TEST_DATABASE_URL must identify a database whose name contains 'test'")
    return database_url


@pytest.fixture(scope="module")
def correlation_engine() -> Generator[Engine, None, None]:
    database_url = _test_database_url()
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    command.upgrade(config, "head")
    engine = create_engine(database_url, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture
def correlation_session(correlation_engine: Engine) -> Generator[Session, None, None]:
    with correlation_engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            yield session
        transaction.rollback()


@pytest.fixture
def correlation_client(correlation_session: Session) -> Generator[TestClient, None, None]:
    def override_database() -> Generator[Session, None, None]:
        yield correlation_session

    app.dependency_overrides[get_db] = override_database
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def _seed(correlation_session: Session, *, with_events: bool = True) -> dict[str, object]:
    case = Case(
        id=CASE_ID,
        case_number="TEST-CORRELATION-CASE",
        name="Synthetic correlation test",
        status=CaseStatus.OPEN,
    )
    evidence = Evidence(
        id=EVIDENCE_ID,
        case_id=CASE_ID,
        evidence_number="TEST-CORRELATION-EVIDENCE",
        name="synthetic.bin",
        evidence_type=EvidenceType.FILE,
    )
    digest = "b" * 64
    evidence_hash = EvidenceHash(
        evidence_id=EVIDENCE_ID,
        algorithm="SHA256",
        digest=digest,
        purpose="ACQUISITION",
    )
    custody = ChainOfCustodyEntry(
        evidence_id=EVIDENCE_ID,
        timestamp=BASE_TIME,
        person="Test Custodian",
        action="REGISTERED",
    )
    correlation_session.add_all([case, evidence, evidence_hash, custody])
    correlation_session.flush()
    if not with_events:
        correlation_session.commit()
        return {"digest": digest}

    definitions = (
        (
            ArtifactType.EVTX,
            TimelineEventType.EVTX_EVENT,
            0,
            {
                "event_id": 4688,
                "channel": "Security",
                "process_path": "C:\\Windows\\System32\\powershell.exe",
                "process_name": "powershell.exe",
            },
        ),
        (
            ArtifactType.PREFETCH,
            TimelineEventType.PREFETCH_EXECUTION,
            10,
            {"application_name": "POWERSHELL.EXE"},
        ),
        (
            ArtifactType.LNK,
            TimelineEventType.LNK_METADATA_MODIFICATION,
            20,
            {"target_path": "c:/windows/system32/POWERSHELL.EXE"},
        ),
        (
            ArtifactType.NTFS_MFT,
            TimelineEventType.NTFS_SI_MODIFICATION,
            30,
            {"filename": "PowerShell.exe", "timestamp_family": "$STANDARD_INFORMATION"},
        ),
        (
            ArtifactType.REGISTRY,
            TimelineEventType.REGISTRY_KEY_LAST_WRITE,
            40,
            {"hive": "SOFTWARE", "key_path": "ROOT\\Software\\PowerShell"},
        ),
    )
    events: list[TimelineEvent] = []
    artifacts: list[Artifact] = []
    records: list[ArtifactRecord] = []
    for index, (artifact_type, event_type, seconds, metadata) in enumerate(definitions, start=1):
        artifact = Artifact(
            id=uuid.UUID(int=5100 + index),
            evidence_id=EVIDENCE_ID,
            artifact_type=artifact_type,
            parser_name=f"TEST_{artifact_type.value}",
            parser_version="1.0.0",
            status=ParserExecutionStatus.COMPLETED,
            metadata_={},
            warnings=[],
            errors=[],
            statistics={},
        )
        record = ArtifactRecord(
            id=uuid.UUID(int=5200 + index),
            artifact_id=artifact.id,
            record_type=f"TEST_{artifact_type.value}",
            source_record_identifier=f"record-{index}",
            event_time=BASE_TIME + timedelta(seconds=seconds),
            data={"source": index},
            provenance={"evidence_id": str(EVIDENCE_ID)},
        )
        event = TimelineEvent(
            id=uuid.UUID(int=5300 + index),
            case_id=CASE_ID,
            evidence_id=EVIDENCE_ID,
            artifact_id=artifact.id,
            artifact_record_id=record.id,
            parser_name=artifact.parser_name,
            parser_version=artifact.parser_version,
            artifact_type=artifact_type,
            event_type=event_type,
            event_time=record.event_time,
            raw_time=str(seconds),
            time_source=f"test.time.{index}",
            time_semantics="Synthetic isolated integration observation",
            timestamp_precision=TimestampPrecision.SECOND,
            event_ordinal=0,
            description="Synthetic isolated integration observation",
            source_identifier=f"timeline-{index}",
            metadata_=metadata,
            provenance={"artifact_record_id": str(record.id)},
        )
        correlation_session.add_all([artifact, record, event])
        artifacts.append(artifact)
        records.append(record)
        events.append(event)
    correlation_session.commit()
    return {
        "digest": digest,
        "events": events,
        "artifacts": artifacts,
        "records": records,
    }


def test_correlation_run_is_idempotent_auditable_and_preserves_provenance(
    correlation_client: TestClient, correlation_session: Session
) -> None:
    seeded = _seed(correlation_session)
    artifacts = cast(list[Artifact], seeded["artifacts"])
    records = cast(list[ArtifactRecord], seeded["records"])
    events = cast(list[TimelineEvent], seeded["events"])
    digest = cast(str, seeded["digest"])
    artifact_snapshots = [(item.id, dict(item.metadata_)) for item in artifacts]
    record_snapshots = [(item.id, dict(item.data)) for item in records]
    event_snapshots = [
        (item.id, item.event_time, dict(item.metadata_), dict(item.provenance)) for item in events
    ]

    first = correlation_client.post(f"/api/cases/{CASE_ID}/correlation/run")
    assert first.status_code == 200, first.text
    assert first.json()["event_count"] == 5
    assert first.json()["matched_count"] == 3
    assert first.json()["finding_count"] == 3
    assert first.json()["status"] == "COMPLETED_WITH_WARNINGS"
    assert len(first.json()["rules_evaluated"]) == 4
    assert "REGISTRY" in first.json()["warnings"][0]

    second = correlation_client.post(f"/api/cases/{CASE_ID}/correlation/run")
    assert second.status_code == 200
    assert second.json()["matched_count"] == 0
    assert second.json()["finding_count"] == 0
    assert correlation_session.scalar(select(func.count()).select_from(CorrelationRun)) == 2
    assert correlation_session.scalar(select(func.count()).select_from(CorrelationMatch)) == 3
    assert correlation_session.scalar(select(func.count()).select_from(Finding)) == 3
    assert correlation_session.scalar(select(func.count()).select_from(CorrelationMatchEvent)) == 6

    matches = correlation_client.get(f"/api/cases/{CASE_ID}/correlations", params={"limit": 100})
    assert matches.status_code == 200
    assert matches.json()["meta"]["total"] == 3
    assert all(len(item["timeline_event_ids"]) == 2 for item in matches.json()["data"])
    assert all(len(item["supporting_events"]) == 2 for item in matches.json()["data"])
    findings = correlation_client.get(f"/api/cases/{CASE_ID}/findings", params={"limit": 100})
    assert findings.status_code == 200
    assert findings.json()["meta"]["total"] == 3
    assert all(len(item["timeline_event_ids"]) == 2 for item in findings.json()["data"])
    assert all(len(item["supporting_events"]) == 2 for item in findings.json()["data"])
    assert all(
        "does not establish malicious" in item["description"] for item in findings.json()["data"]
    )

    finding = correlation_session.scalar(
        select(Finding).where(Finding.rule_id == "CORR-EVTX-PREFETCH-001")
    )
    assert finding is not None
    match = correlation_session.get(CorrelationMatch, finding.correlation_match_id)
    assert match is not None and match.rule_version == "1.0.0"
    links = list(
        correlation_session.scalars(
            select(CorrelationMatchEvent).where(
                CorrelationMatchEvent.correlation_match_id == match.id
            )
        )
    )
    for link in links:
        event = correlation_session.get(TimelineEvent, link.timeline_event_id)
        assert event is not None
        record = correlation_session.get(ArtifactRecord, event.artifact_record_id)
        assert record is not None
        artifact = correlation_session.get(Artifact, record.artifact_id)
        assert artifact is not None and artifact.evidence_id == EVIDENCE_ID
    assert (
        correlation_session.scalar(
            select(EvidenceHash.digest).where(EvidenceHash.evidence_id == EVIDENCE_ID)
        )
        == digest
    )
    assert (
        correlation_session.scalar(
            select(func.count())
            .select_from(ChainOfCustodyEntry)
            .where(ChainOfCustodyEntry.evidence_id == EVIDENCE_ID)
        )
        == 1
    )
    assert [(item.id, dict(item.metadata_)) for item in artifacts] == artifact_snapshots
    assert [(item.id, dict(item.data)) for item in records] == record_snapshots
    assert [
        (item.id, item.event_time, dict(item.metadata_), dict(item.provenance)) for item in events
    ] == event_snapshots
    audits = list(
        correlation_session.scalars(
            select(AuditEvent).where(AuditEvent.case_id == CASE_ID).order_by(AuditEvent.action)
        )
    )
    assert sum(item.action == "CORRELATION_RUN" for item in audits) == 2
    assert sum(item.action == "FINDING_CREATED" for item in audits) == 3


def test_finding_lifecycle_updates_are_controlled_and_audited(
    correlation_client: TestClient, correlation_session: Session
) -> None:
    _seed(correlation_session)
    correlation_client.post(f"/api/cases/{CASE_ID}/correlation/run")
    finding = correlation_session.scalar(select(Finding).order_by(Finding.deterministic_key))
    assert finding is not None
    original_rule = (finding.rule_id, finding.rule_version, finding.correlation_match_id)
    response = correlation_client.patch(
        f"/api/findings/{finding.id}",
        json={
            "status": "REVIEWED",
            "severity": "HIGH",
            "confidence": "HIGH",
            "analyst_notes": "Examiner review note.",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "REVIEWED"
    assert response.json()["severity"] == "HIGH"
    assert response.json()["confidence"] == "HIGH"
    assert response.json()["analyst_notes"] == "Examiner review note."
    assert (response.json()["rule_id"], response.json()["rule_version"]) == original_rule[:2]
    immutable = correlation_client.patch(f"/api/findings/{finding.id}", json={"rule_id": "CHANGED"})
    assert immutable.status_code == 422
    assert (
        correlation_client.patch(
            f"/api/findings/{finding.id}", json={"status": "INVALID"}
        ).status_code
        == 422
    )
    assert (
        correlation_client.patch(
            f"/api/findings/{finding.id}", json={"severity": "INVALID"}
        ).status_code
        == 422
    )
    assert (
        correlation_client.patch(
            f"/api/findings/{finding.id}", json={"confidence": "INVALID"}
        ).status_code
        == 422
    )
    resolved = correlation_client.patch(f"/api/findings/{finding.id}", json={"status": "RESOLVED"})
    assert resolved.status_code == 200
    conflict = correlation_client.patch(f"/api/findings/{finding.id}", json={"status": "REVIEWED"})
    assert conflict.status_code == 409
    correlation_session.refresh(finding)
    assert (finding.rule_id, finding.rule_version, finding.correlation_match_id) == original_rule
    actions = list(
        correlation_session.scalars(select(AuditEvent.action).where(AuditEvent.case_id == CASE_ID))
    )
    assert actions.count("FINDING_UPDATED") == 2
    assert actions.count("FINDING_STATUS_CHANGED") == 2


def test_empty_case_and_missing_resources(
    correlation_client: TestClient, correlation_session: Session
) -> None:
    _seed(correlation_session, with_events=False)
    response = correlation_client.post(f"/api/cases/{CASE_ID}/correlation/run")
    assert response.status_code == 200
    assert response.json()["event_count"] == 0
    assert response.json()["matched_count"] == 0
    assert response.json()["finding_count"] == 0
    missing = uuid.uuid4()
    assert correlation_client.post(f"/api/cases/{missing}/correlation/run").status_code == 404
    assert correlation_client.get(f"/api/cases/{missing}/correlations").status_code == 404
    assert correlation_client.get(f"/api/cases/{missing}/findings").status_code == 404
    assert correlation_client.get(f"/api/findings/{missing}").status_code == 404
