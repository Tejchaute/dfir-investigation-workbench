import os
import uuid
from collections.abc import Generator
from datetime import UTC, datetime

import pytest
from alembic.config import Config
from sqlalchemy import Engine, create_engine, inspect
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from alembic import command
from app.db.models import AuditEvent, Case, ChainOfCustodyEntry, Evidence, EvidenceHash
from app.domain.enums import CaseStatus, EvidenceType


def _test_database_url() -> str:
    database_url = os.getenv("TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration tests")
    database_name = make_url(database_url).database or ""
    if "test" not in database_name.lower():
        pytest.fail("TEST_DATABASE_URL must identify a database whose name contains 'test'")
    return database_url


@pytest.fixture(scope="module")
def migrated_engine() -> Generator[Engine, None, None]:
    database_url = _test_database_url()
    alembic_config = Config("alembic.ini")
    alembic_config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))

    previous_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    try:
        command.downgrade(alembic_config, "base")
        command.upgrade(alembic_config, "head")
        assert set(inspect(create_engine(database_url)).get_table_names()) >= {
            "cases",
            "evidence",
            "evidence_hashes",
            "chain_of_custody_entries",
            "audit_events",
        }
        command.downgrade(alembic_config, "-1")
        command.upgrade(alembic_config, "head")
        engine = create_engine(database_url, pool_pre_ping=True)
        yield engine
        engine.dispose()
    finally:
        if previous_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_url


@pytest.fixture
def session(migrated_engine: Engine) -> Generator[Session, None, None]:
    with migrated_engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as database_session:
            yield database_session
        transaction.rollback()


def _case(case_number: str) -> Case:
    return Case(case_number=case_number, name="Synthetic persistence test", status=CaseStatus.OPEN)


def _evidence(case_id: uuid.UUID, evidence_number: str) -> Evidence:
    return Evidence(
        case_id=case_id,
        evidence_number=evidence_number,
        name="Synthetic metadata record",
        evidence_type=EvidenceType.FILE,
    )


def test_case_can_be_persisted_and_case_number_is_unique(session: Session) -> None:
    first = _case("TEST-CASE-UNIQUE")
    session.add(first)
    session.commit()
    assert session.get(Case, first.id) is first

    session.add(_case("TEST-CASE-UNIQUE"))
    with pytest.raises(IntegrityError):
        session.commit()


def test_evidence_requires_case_and_has_scoped_number(session: Session) -> None:
    missing_case_evidence = _evidence(uuid.uuid4(), "TEST-EVIDENCE-MISSING-CASE")
    session.add(missing_case_evidence)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()

    case = _case("TEST-CASE-EVIDENCE")
    session.add(case)
    session.flush()
    evidence = _evidence(case.id, "TEST-EVIDENCE-1")
    session.add(evidence)
    session.commit()
    assert evidence.case.id == case.id
    assert evidence in case.evidence_items

    session.add(_evidence(case.id, "TEST-EVIDENCE-1"))
    with pytest.raises(IntegrityError):
        session.commit()


def test_same_evidence_number_is_allowed_in_different_cases(session: Session) -> None:
    first_case = _case("TEST-CASE-SCOPE-A")
    second_case = _case("TEST-CASE-SCOPE-B")
    session.add_all([first_case, second_case])
    session.flush()
    session.add_all(
        [
            _evidence(first_case.id, "TEST-EVIDENCE-SHARED"),
            _evidence(second_case.id, "TEST-EVIDENCE-SHARED"),
        ]
    )
    session.commit()


def test_multiple_hashes_and_custody_belong_to_evidence(session: Session) -> None:
    case = _case("TEST-CASE-PROVENANCE")
    session.add(case)
    session.flush()
    evidence = _evidence(case.id, "TEST-EVIDENCE-PROVENANCE")
    session.add(evidence)
    session.flush()
    first_hash = EvidenceHash(
        evidence_id=evidence.id,
        algorithm="SHA-256",
        digest="0" * 64,
        purpose="INITIAL_TEST_RECORD",
    )
    second_hash = EvidenceHash(
        evidence_id=evidence.id,
        algorithm="SHA-256",
        digest="1" * 64,
        purpose="REVERIFICATION_TEST_RECORD",
    )
    custody = ChainOfCustodyEntry(
        evidence_id=evidence.id,
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        person="Test Actor",
        action="TEST_ACTION",
    )
    session.add_all([first_hash, second_hash, custody])
    session.commit()
    assert {item.id for item in evidence.hashes} == {first_hash.id, second_hash.id}
    assert custody in evidence.custody_entries


def test_audit_event_supports_case_and_optional_evidence(session: Session) -> None:
    case = _case("TEST-CASE-AUDIT")
    session.add(case)
    session.flush()
    evidence = _evidence(case.id, "TEST-EVIDENCE-AUDIT")
    session.add(evidence)
    session.flush()
    case_event = AuditEvent(
        case_id=case.id,
        action="TEST_CASE_ACTION",
        actor="Test Actor",
        details={"scope": "case"},
    )
    evidence_event = AuditEvent(
        case_id=case.id,
        evidence_id=evidence.id,
        action="TEST_EVIDENCE_ACTION",
        actor="Test Actor",
        details={"scope": "evidence"},
    )
    session.add_all([case_event, evidence_event])
    session.commit()
    assert case_event.evidence is None
    assert evidence_event.evidence is evidence
    assert evidence_event.details == {"scope": "evidence"}


def test_parent_deletion_is_restricted(session: Session) -> None:
    case = _case("TEST-CASE-DELETE-RESTRICT")
    session.add(case)
    session.flush()
    session.add(_evidence(case.id, "TEST-EVIDENCE-DELETE-RESTRICT"))
    session.commit()
    session.delete(case)
    with pytest.raises(IntegrityError):
        session.commit()
