"""Add generic parser framework persistence.

Revision ID: 0004_parser_framework
Revises: 0003_evidence_number_sequence
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004_parser_framework"
down_revision: str | None = "0003_evidence_number_sequence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evidence_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("artifact_type", sa.String(length=9), nullable=False),
        sa.Column("parser_name", sa.String(length=255), nullable=False),
        sa.Column("parser_version", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=23), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("warnings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("errors", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("statistics", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "artifact_type IN ('REFERENCE', 'EVTX', 'REGISTRY', 'PREFETCH', 'LNK', 'NTFS')",
            name="artifact_type",
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'RUNNING', 'COMPLETED', 'COMPLETED_WITH_WARNINGS', "
            "'FAILED', 'UNSUPPORTED')",
            name="parser_execution_status",
        ),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_artifacts_evidence_id", "artifacts", ["evidence_id"])
    op.create_index("ix_artifacts_artifact_type", "artifacts", ["artifact_type"])
    op.create_index("ix_artifacts_status", "artifacts", ["status"])
    op.create_index("ix_artifacts_created_at", "artifacts", ["created_at"])

    op.create_table(
        "artifact_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("artifact_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("record_type", sa.String(length=255), nullable=False),
        sa.Column("source_record_identifier", sa.String(length=500), nullable=True),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["artifact_id"], ["artifacts.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_artifact_records_artifact_id", "artifact_records", ["artifact_id"])
    op.create_index("ix_artifact_records_event_time", "artifact_records", ["event_time"])
    op.create_index("ix_artifact_records_record_type", "artifact_records", ["record_type"])


def downgrade() -> None:
    op.drop_index("ix_artifact_records_record_type", table_name="artifact_records")
    op.drop_index("ix_artifact_records_event_time", table_name="artifact_records")
    op.drop_index("ix_artifact_records_artifact_id", table_name="artifact_records")
    op.drop_table("artifact_records")
    op.drop_index("ix_artifacts_created_at", table_name="artifacts")
    op.drop_index("ix_artifacts_status", table_name="artifacts")
    op.drop_index("ix_artifacts_artifact_type", table_name="artifacts")
    op.drop_index("ix_artifacts_evidence_id", table_name="artifacts")
    op.drop_table("artifacts")
