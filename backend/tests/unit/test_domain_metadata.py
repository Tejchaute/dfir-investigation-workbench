from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from app.db import models  # noqa: F401
from app.db.base import Base


def test_domain_metadata_contains_expected_tables() -> None:
    assert set(Base.metadata.tables) == {
        "cases",
        "evidence",
        "evidence_hashes",
        "chain_of_custody_entries",
        "audit_events",
        "artifacts",
        "artifact_records",
        "timeline_events",
    }


def test_postgresql_uuid_and_jsonb_types_compile() -> None:
    dialect = postgresql.dialect()  # type: ignore[no-untyped-call]
    cases_sql = str(CreateTable(Base.metadata.tables["cases"]).compile(dialect=dialect))
    audit_sql = str(CreateTable(Base.metadata.tables["audit_events"]).compile(dialect=dialect))
    artifact_sql = str(CreateTable(Base.metadata.tables["artifacts"]).compile(dialect=dialect))
    assert "UUID" in cases_sql
    assert "JSONB" in audit_sql
    assert "UUID" in artifact_sql
    assert "JSONB" in artifact_sql


def test_forensic_foreign_keys_restrict_deletion() -> None:
    foreign_keys = {
        foreign_key for table in Base.metadata.tables.values() for foreign_key in table.foreign_keys
    }
    assert foreign_keys
    assert all(foreign_key.ondelete == "RESTRICT" for foreign_key in foreign_keys)
