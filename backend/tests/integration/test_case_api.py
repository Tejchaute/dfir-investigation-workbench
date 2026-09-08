import os
import re
import uuid
from collections.abc import Generator
from datetime import UTC, datetime
from typing import cast

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from alembic import command
from app.core.exceptions import InfrastructureError
from app.db.models import AuditEvent, Case
from app.db.session import get_db
from app.domain.enums import CaseStatus
from app.main import app
from app.schemas.case import CaseCreate
from app.services.case_service import LOCAL_AUDIT_ACTOR, case_service


def _test_database_url() -> str:
    database_url = os.getenv("TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration tests")
    if "test" not in (make_url(database_url).database or "").lower():
        pytest.fail("TEST_DATABASE_URL must identify a database whose name contains 'test'")
    return database_url


@pytest.fixture(scope="module")
def case_engine() -> Generator[Engine, None, None]:
    database_url = _test_database_url()
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    command.upgrade(config, "head")
    engine = create_engine(database_url, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture
def case_session(case_engine: Engine) -> Generator[Session, None, None]:
    with case_engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            yield session
        transaction.rollback()


@pytest.fixture
def client(case_session: Session) -> Generator[TestClient, None, None]:
    def override_database() -> Generator[Session, None, None]:
        yield case_session

    app.dependency_overrides[get_db] = override_database
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _create_case(client: TestClient, name: str = "Synthetic API test") -> dict[str, object]:
    response = client.post(
        "/api/cases",
        json={"name": name, "description": "Test-only metadata", "investigator": "Test Actor"},
    )
    assert response.status_code == 201
    return cast(dict[str, object], response.json())


def test_create_case_generates_number_and_atomic_audit(
    client: TestClient, case_session: Session
) -> None:
    response_data = _create_case(client)
    assert response_data["status"] == "OPEN"
    assert re.fullmatch(
        rf"CASE-{datetime.now(UTC).year}-\d{{4,}}", str(response_data["case_number"])
    )

    case_id = uuid.UUID(str(response_data["id"]))
    audit = case_session.scalar(
        select(AuditEvent).where(AuditEvent.case_id == case_id, AuditEvent.action == "CASE_CREATED")
    )
    assert audit is not None
    assert audit.actor == LOCAL_AUDIT_ACTOR
    assert audit.details == {"case_number": response_data["case_number"], "status": "OPEN"}


def test_creation_rejects_server_controlled_fields(client: TestClient) -> None:
    response = client.post(
        "/api/cases",
        json={"name": "Synthetic invalid request", "status": "ARCHIVED", "case_number": "BAD"},
    )
    assert response.status_code == 422


def test_list_cases_is_paginated_and_deterministic(client: TestClient) -> None:
    _create_case(client, "Synthetic list first")
    second = _create_case(client, "Synthetic list second")
    response = client.get("/api/cases", params={"limit": 1, "offset": 0})
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["limit"] == 1
    assert body["meta"]["offset"] == 0
    assert body["meta"]["total"] >= 2
    assert body["data"][0]["id"] == second["id"]

    invalid_limit = client.get("/api/cases", params={"limit": 101})
    assert invalid_limit.status_code == 422


def test_get_and_update_case_create_audit(client: TestClient, case_session: Session) -> None:
    created = _create_case(client)
    case_id = str(created["id"])
    get_response = client.get(f"/api/cases/{case_id}")
    assert get_response.status_code == 200

    original_updated_at = get_response.json()["updated_at"]
    update_response = client.patch(
        f"/api/cases/{case_id}",
        json={"name": "Updated synthetic name", "description": None},
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Updated synthetic name"
    assert update_response.json()["description"] is None
    assert update_response.json()["updated_at"] >= original_updated_at

    audit = case_session.scalar(
        select(AuditEvent).where(
            AuditEvent.case_id == uuid.UUID(case_id), AuditEvent.action == "CASE_UPDATED"
        )
    )
    assert audit is not None
    assert audit.details == {"fields": ["description", "name"]}


def test_update_rejects_empty_or_protected_fields(client: TestClient) -> None:
    created = _create_case(client)
    case_id = str(created["id"])
    assert client.patch(f"/api/cases/{case_id}", json={}).status_code == 422
    assert client.patch(f"/api/cases/{case_id}", json={"status": "CLOSED"}).status_code == 422
    assert client.patch(f"/api/cases/{case_id}", json={"name": "   "}).status_code == 422


def test_case_lifecycle_and_audits(client: TestClient, case_session: Session) -> None:
    created = _create_case(client)
    case_id = str(created["id"])
    assert client.post(f"/api/cases/{case_id}/archive").status_code == 409

    closed = client.post(f"/api/cases/{case_id}/close")
    assert closed.status_code == 200
    assert closed.json()["status"] == "CLOSED"
    assert client.post(f"/api/cases/{case_id}/close").status_code == 409

    archived = client.post(f"/api/cases/{case_id}/archive")
    assert archived.status_code == 200
    assert archived.json()["status"] == "ARCHIVED"
    assert client.post(f"/api/cases/{case_id}/close").status_code == 409
    assert client.post(f"/api/cases/{case_id}/archive").status_code == 409

    actions = set(
        case_session.scalars(
            select(AuditEvent.action).where(AuditEvent.case_id == uuid.UUID(case_id))
        )
    )
    assert actions == {"CASE_CREATED", "CASE_CLOSED", "CASE_ARCHIVED"}


def test_missing_case_returns_not_found(client: TestClient) -> None:
    missing_id = uuid.uuid4()
    assert client.get(f"/api/cases/{missing_id}").status_code == 404
    assert client.patch(f"/api/cases/{missing_id}", json={"name": "Missing"}).status_code == 404
    assert client.post(f"/api/cases/{missing_id}/close").status_code == 404


def test_create_rolls_back_when_commit_fails(
    case_engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    case_name = f"Synthetic rollback {uuid.uuid4()}"
    with Session(case_engine) as session:

        def fail_commit() -> None:
            raise SQLAlchemyError("synthetic commit failure")

        monkeypatch.setattr(session, "commit", fail_commit)
        with pytest.raises(InfrastructureError, match="Case creation failed"):
            case_service.create(session, CaseCreate(name=case_name))

    with Session(case_engine) as verification_session:
        count = verification_session.scalar(
            select(func.count()).select_from(Case).where(Case.name == case_name)
        )
    assert count == 0


def test_status_is_not_mutated_by_metadata_update(client: TestClient) -> None:
    created = _create_case(client)
    case_id = str(created["id"])
    client.post(f"/api/cases/{case_id}/close")
    response = client.patch(f"/api/cases/{case_id}", json={"investigator": None})
    assert response.status_code == 200
    assert response.json()["status"] == CaseStatus.CLOSED.value
