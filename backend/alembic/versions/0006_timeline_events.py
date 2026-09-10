"""Add persistent normalized timeline events.

Revision ID: 0006_timeline_events
Revises: 0005_ntfs_mft_type
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0006_timeline_events"
down_revision: str | None = "0005_ntfs_mft_type"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "timeline_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evidence_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("artifact_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("artifact_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parser_name", sa.String(length=255), nullable=False),
        sa.Column("parser_version", sa.String(length=100), nullable=False),
        sa.Column("artifact_type", sa.String(length=9), nullable=False),
        sa.Column("event_type", sa.String(length=25), nullable=False),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_time", sa.String(length=255), nullable=True),
        sa.Column("time_source", sa.String(length=255), nullable=False),
        sa.Column("time_semantics", sa.String(length=255), nullable=False),
        sa.Column("timestamp_precision", sa.String(length=11), nullable=False),
        sa.Column("event_ordinal", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=False),
        sa.Column("source_identifier", sa.String(length=500), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "artifact_type IN "
            "('REFERENCE', 'EVTX', 'REGISTRY', 'PREFETCH', 'LNK', 'NTFS', 'NTFS_MFT')",
            name="timeline_artifact_type",
        ),
        sa.CheckConstraint(
            "event_type IN ('EVTX_EVENT', 'REGISTRY_KEY_LAST_WRITE', 'PREFETCH_EXECUTION', "
            "'LNK_METADATA_CREATION', 'LNK_METADATA_ACCESS', 'LNK_METADATA_MODIFICATION', "
            "'NTFS_SI_CREATION', 'NTFS_SI_MODIFICATION', 'NTFS_SI_MFT_CHANGE', "
            "'NTFS_SI_ACCESS', 'NTFS_FN_CREATION', 'NTFS_FN_MODIFICATION', "
            "'NTFS_FN_MFT_CHANGE', 'NTFS_FN_ACCESS')",
            name="timeline_event_type",
        ),
        sa.CheckConstraint(
            "timestamp_precision IN ('SECOND', 'MILLISECOND', 'MICROSECOND', '100NS', 'UNKNOWN')",
            name="timestamp_precision",
        ),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["artifact_id"], ["artifacts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["artifact_record_id"], ["artifact_records.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "artifact_record_id",
            "event_type",
            "time_source",
            "event_ordinal",
            name="uq_timeline_events_logical_identity",
        ),
    )
    for index, column in (
        ("ix_timeline_events_case_id", "case_id"),
        ("ix_timeline_events_evidence_id", "evidence_id"),
        ("ix_timeline_events_artifact_id", "artifact_id"),
        ("ix_timeline_events_artifact_record_id", "artifact_record_id"),
        ("ix_timeline_events_event_time", "event_time"),
        ("ix_timeline_events_event_type", "event_type"),
        ("ix_timeline_events_artifact_type", "artifact_type"),
        ("ix_timeline_events_source_identifier", "source_identifier"),
    ):
        op.create_index(index, "timeline_events", [column])


def downgrade() -> None:
    for index in (
        "ix_timeline_events_source_identifier",
        "ix_timeline_events_artifact_type",
        "ix_timeline_events_event_type",
        "ix_timeline_events_event_time",
        "ix_timeline_events_artifact_record_id",
        "ix_timeline_events_artifact_id",
        "ix_timeline_events_evidence_id",
        "ix_timeline_events_case_id",
    ):
        op.drop_index(index, table_name="timeline_events")
    op.drop_table("timeline_events")
