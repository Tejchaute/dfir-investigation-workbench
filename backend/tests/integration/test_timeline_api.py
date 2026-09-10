import os
import uuid
from collections.abc import Generator
from datetime import UTC, datetime

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
    Evidence,
    EvidenceHash,
    TimelineEvent,
)
from app.db.session import get_db
from app.domain.enums import ArtifactType, CaseStatus, EvidenceType, ParserExecutionStatus
from app.main import app

CASE_ID = uuid.UUID(int=100)
EVIDENCE_ID = uuid.UUID(int=101)


def _test_database_url() -> str:
    database_url = os.getenv("TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration tests")
    if "test" not in (make_url(database_url).database or "").lower():
        pytest.fail("TEST_DATABASE_URL must identify a database whose name contains 'test'")
    return database_url


@pytest.fixture(scope="module")
def timeline_engine() -> Generator[Engine, None, None]:
    database_url = _test_database_url()
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    command.upgrade(config, "head")
    engine = create_engine(database_url, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture
def timeline_session(timeline_engine: Engine) -> Generator[Session, None, None]:
    with timeline_engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            yield session
        transaction.rollback()


@pytest.fixture
def timeline_client(timeline_session: Session) -> Generator[TestClient, None, None]:
    def override_database() -> Generator[Session, None, None]:
        yield timeline_session

    app.dependency_overrides[get_db] = override_database
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def _seed(session: Session) -> tuple[str, int]:
    case = Case(
        id=CASE_ID,
        case_number="TEST-TIMELINE-CASE",
        name="Synthetic timeline test",
        status=CaseStatus.OPEN,
    )
    evidence = Evidence(
        id=EVIDENCE_ID,
        case_id=CASE_ID,
        evidence_number="TEST-TIMELINE-EVIDENCE",
        name="synthetic.bin",
        evidence_type=EvidenceType.FILE,
    )
    digest = "a" * 64
    hash_record = EvidenceHash(
        evidence_id=EVIDENCE_ID,
        algorithm="SHA256",
        digest=digest,
        purpose="ACQUISITION",
    )
    custody = ChainOfCustodyEntry(
        evidence_id=EVIDENCE_ID,
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        person="Test Custodian",
        action="REGISTERED",
    )
    session.add_all([case, evidence, hash_record, custody])
    session.flush()
    definitions = [
        (
            ArtifactType.EVTX,
            "EVTX_EVENT",
            {
                "event_timestamp": "2026-01-02T03:04:05.123Z",
                "event_id": 4688,
                "provider": "Provider",
                "channel": "Security",
                "computer": "HOST",
                "level": 4,
            },
            datetime(2026, 1, 2, 3, 4, 5, 123000, tzinfo=UTC),
        ),
        (
            ArtifactType.REGISTRY,
            "REGISTRY_KEY",
            {
                "key_last_write_time": "2026-01-02T03:04:05",
                "key_path": "ROOT\\Software",
                "hive_type": "SOFTWARE",
            },
            None,
        ),
        (
            ArtifactType.PREFETCH,
            "PREFETCH_FILE",
            {
                "execution_times": [
                    "2026-01-02T03:04:05.123000+00:00",
                    "2026-01-01T03:04:05.123000+00:00",
                ],
                "execution_time_filetime_values": ["134000000000000000", "133000000000000000"],
                "application_name": "APP.EXE",
                "executable_hash": "12345678",
                "source_prefetch_filename": "APP.EXE-12345678.pf",
                "run_count": 2,
            },
            None,
        ),
        (
            ArtifactType.LNK,
            "SHELL_LINK",
            {
                "creation_time": "2026-01-02T03:04:05.123000+00:00",
                "creation_time_filetime": "134000000000000000",
                "access_time": "2026-01-03T03:04:05.123000+00:00",
                "access_time_filetime": "134001000000000000",
                "modification_time": "2026-01-04T03:04:05.123000+00:00",
                "modification_time_filetime": "134002000000000000",
                "target_path": "C:\\Tools\\app.exe",
            },
            None,
        ),
        (
            ArtifactType.NTFS_MFT,
            "NTFS_MFT_RECORD",
            _ntfs_data(),
            None,
        ),
    ]
    for index, (artifact_type, record_type, data, event_time) in enumerate(definitions, start=1):
        artifact = Artifact(
            id=uuid.UUID(int=200 + index),
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
        session.add(artifact)
        session.flush()
        session.add(
            ArtifactRecord(
                id=uuid.UUID(int=300 + index),
                artifact_id=artifact.id,
                record_type=record_type,
                source_record_identifier=f"source-{index}",
                event_time=event_time,
                data=data,
                provenance={"source_index": index},
            )
        )
    session.commit()
    return digest, 1


def _ntfs_data() -> dict[str, object]:
    def timestamps(year: int) -> dict[str, object]:
        return {
            "creation_time": f"{year}-01-01T00:00:00+00:00",
            "creation_time_filetime": "1",
            "modification_time": f"{year}-01-02T00:00:00+00:00",
            "modification_time_filetime": "2",
            "mft_change_time": f"{year}-01-03T00:00:00+00:00",
            "mft_change_time_filetime": "3",
            "access_time": f"{year}-01-04T00:00:00+00:00",
            "access_time_filetime": "4",
        }

    return {
        "record_number": 42,
        "source_record_offset": 1024,
        "standard_information": timestamps(2020),
        "file_names": [
            {
                **timestamps(2021),
                "filename": "example.txt",
                "parent_directory_reference": {"record_number": 5, "sequence_number": 2},
            }
        ],
    }


def test_generation_query_filters_ordering_idempotency_and_provenance(
    timeline_client: TestClient, timeline_session: Session
) -> None:
    digest_before, custody_before = _seed(timeline_session)
    first = timeline_client.post(f"/api/cases/{CASE_ID}/timeline/generate")
    assert first.status_code == 200, first.text
    assert first.json()["artifacts_considered"] == 5
    assert first.json()["records_considered"] == 5
    assert first.json()["events_created"] == 15
    assert first.json()["events_skipped"] == 0

    second = timeline_client.post(f"/api/cases/{CASE_ID}/timeline/generate")
    assert second.status_code == 200
    assert second.json()["events_created"] == 0
    assert second.json()["events_skipped"] == 15
    assert timeline_session.scalar(select(func.count()).select_from(TimelineEvent)) == 15

    page_one = timeline_client.get(
        f"/api/cases/{CASE_ID}/timeline", params={"limit": 5, "offset": 0}
    )
    page_two = timeline_client.get(
        f"/api/cases/{CASE_ID}/timeline", params={"limit": 5, "offset": 5}
    )
    repeat = timeline_client.get(f"/api/cases/{CASE_ID}/timeline", params={"limit": 5, "offset": 0})
    assert page_one.status_code == 200 and page_two.status_code == 200
    assert page_one.json()["meta"]["total"] == 15
    assert [item["id"] for item in page_one.json()["data"]] == [
        item["id"] for item in repeat.json()["data"]
    ]
    assert not (
        {item["id"] for item in page_one.json()["data"]}
        & {item["id"] for item in page_two.json()["data"]}
    )
    for item in page_one.json()["data"] + page_two.json()["data"]:
        assert item["case_id"] == str(CASE_ID)
        assert item["evidence_id"] == str(EVIDENCE_ID)
        assert item["artifact_id"]
        assert item["artifact_record_id"]
        assert item["provenance"]["artifact_record_id"] == item["artifact_record_id"]

    ntfs = timeline_client.get(
        f"/api/cases/{CASE_ID}/timeline", params={"artifact_type": "NTFS_MFT", "limit": 100}
    )
    assert ntfs.json()["meta"]["total"] == 8
    evtx = timeline_client.get(
        f"/api/cases/{CASE_ID}/timeline", params={"event_type": "EVTX_EVENT"}
    )
    assert evtx.json()["meta"]["total"] == 1
    source = timeline_client.get(
        f"/api/cases/{CASE_ID}/timeline", params={"source_identifier": "source-3"}
    )
    assert source.json()["meta"]["total"] == 2
    date_range = timeline_client.get(
        f"/api/cases/{CASE_ID}/timeline",
        params={
            "start_time": "2026-01-02T03:04:05Z",
            "end_time": "2026-01-02T03:04:06Z",
            "limit": 100,
        },
    )
    assert date_range.status_code == 200 and date_range.json()["meta"]["total"] == 3
    by_evidence = timeline_client.get(
        f"/api/cases/{CASE_ID}/timeline", params={"evidence_id": str(EVIDENCE_ID), "limit": 100}
    )
    assert by_evidence.json()["meta"]["total"] == 15

    audits = list(
        timeline_session.scalars(
            select(AuditEvent).where(
                AuditEvent.case_id == CASE_ID, AuditEvent.action == "TIMELINE_GENERATED"
            )
        )
    )
    assert len(audits) == 2
    assert any(event.details and event.details["events_created"] == 15 for event in audits)
    digest_after = timeline_session.scalar(
        select(EvidenceHash.digest).where(EvidenceHash.evidence_id == EVIDENCE_ID)
    )
    custody_after = timeline_session.scalar(
        select(func.count())
        .select_from(ChainOfCustodyEntry)
        .where(ChainOfCustodyEntry.evidence_id == EVIDENCE_ID)
    )
    assert digest_before == digest_after == "a" * 64
    assert custody_before == custody_after == 1


def test_reparsed_artifact_adds_events_without_replacing_history(
    timeline_client: TestClient, timeline_session: Session
) -> None:
    _seed(timeline_session)
    initial = timeline_client.post(f"/api/cases/{CASE_ID}/timeline/generate")
    assert initial.json()["events_created"] == 15
    artifact = Artifact(
        id=uuid.UUID(int=999),
        evidence_id=EVIDENCE_ID,
        artifact_type=ArtifactType.PREFETCH,
        parser_name="TEST_PREFETCH",
        parser_version="2.0.0",
        status=ParserExecutionStatus.COMPLETED,
        metadata_={},
        warnings=[],
        errors=[],
        statistics={},
    )
    timeline_session.add(artifact)
    timeline_session.flush()
    timeline_session.add(
        ArtifactRecord(
            id=uuid.UUID(int=1000),
            artifact_id=artifact.id,
            record_type="PREFETCH_FILE",
            source_record_identifier="reparse-source",
            data={
                "execution_times": ["2026-02-01T00:00:00+00:00"],
                "execution_time_filetime_values": ["134100000000000000"],
                "application_name": "APP.EXE",
            },
            provenance={},
        )
    )
    timeline_session.commit()
    generated = timeline_client.post(f"/api/cases/{CASE_ID}/timeline/generate")
    assert generated.json()["events_created"] == 1
    assert timeline_session.scalar(select(func.count()).select_from(TimelineEvent)) == 16
    assert (
        timeline_session.scalar(
            select(func.count())
            .select_from(TimelineEvent)
            .where(TimelineEvent.artifact_id == artifact.id)
        )
        == 1
    )


def test_timeline_api_validation_and_missing_case(
    timeline_client: TestClient, timeline_session: Session
) -> None:
    missing = uuid.uuid4()
    assert timeline_client.post(f"/api/cases/{missing}/timeline/generate").status_code == 404
    assert timeline_client.get(f"/api/cases/{missing}/timeline").status_code == 404
    _seed(timeline_session)
    naive = timeline_client.get(
        f"/api/cases/{CASE_ID}/timeline", params={"start_time": "2026-01-01T00:00:00"}
    )
    assert naive.status_code == 422
