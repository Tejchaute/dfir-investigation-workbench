"""Add deterministic correlation runs, matches, and findings.

Revision ID: 0007_correlation_findings
Revises: 0006_timeline_events
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0007_correlation_findings"
down_revision: str | None = "0006_timeline_events"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "correlation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=23), nullable=False),
        sa.Column("rule_set_version", sa.String(length=100), nullable=False),
        sa.Column("temporal_window_seconds", sa.Integer(), nullable=False),
        sa.Column("event_count", sa.Integer(), nullable=False),
        sa.Column("matched_count", sa.Integer(), nullable=False),
        sa.Column("finding_count", sa.Integer(), nullable=False),
        sa.Column("rules_evaluated", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("warnings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("errors", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('RUNNING', 'COMPLETED', 'COMPLETED_WITH_WARNINGS', 'FAILED')",
            name="correlation_run_status",
        ),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_correlation_runs_case_id", "correlation_runs", ["case_id"])
    op.create_index("ix_correlation_runs_status", "correlation_runs", ["status"])
    op.create_index("ix_correlation_runs_created_at", "correlation_runs", ["created_at"])

    op.create_table(
        "correlation_matches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("correlation_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rule_id", sa.String(length=100), nullable=False),
        sa.Column("rule_version", sa.String(length=50), nullable=False),
        sa.Column("deterministic_key", sa.String(length=64), nullable=False),
        sa.Column("temporal_delta_seconds", sa.Float(), nullable=False),
        sa.Column("match_basis", sa.String(length=50), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["correlation_run_id"], ["correlation_runs.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("deterministic_key"),
    )
    op.create_index("ix_correlation_matches_case_id", "correlation_matches", ["case_id"])
    op.create_index("ix_correlation_matches_run_id", "correlation_matches", ["correlation_run_id"])
    op.create_index(
        "ix_correlation_matches_rule",
        "correlation_matches",
        ["rule_id", "rule_version"],
    )
    op.create_index("ix_correlation_matches_created_at", "correlation_matches", ["created_at"])

    op.create_table(
        "correlation_match_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("correlation_match_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timeline_event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_role", sa.String(length=50), nullable=False),
        sa.Column("event_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["correlation_match_id"], ["correlation_matches.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["timeline_event_id"], ["timeline_events.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "correlation_match_id",
            "timeline_event_id",
            name="uq_correlation_match_event",
        ),
    )
    op.create_index(
        "ix_correlation_match_events_match_id",
        "correlation_match_events",
        ["correlation_match_id"],
    )
    op.create_index(
        "ix_correlation_match_events_event_id",
        "correlation_match_events",
        ["timeline_event_id"],
    )

    op.create_table(
        "findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("correlation_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("correlation_match_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("finding_type", sa.String(length=30), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=9), nullable=False),
        sa.Column("severity", sa.String(length=8), nullable=False),
        sa.Column("confidence", sa.String(length=6), nullable=False),
        sa.Column("rule_id", sa.String(length=100), nullable=False),
        sa.Column("rule_version", sa.String(length=50), nullable=False),
        sa.Column("deterministic_key", sa.String(length=64), nullable=False),
        sa.Column("analyst_notes", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "finding_type IN ('PROCESS_EXECUTION_CORROBORATED', 'LNK_PROCESS_ASSOCIATION', "
            "'FILE_ACTIVITY_ASSOCIATION', 'REGISTRY_PROCESS_ASSOCIATION')",
            name="finding_type",
        ),
        sa.CheckConstraint(
            "status IN ('OPEN', 'REVIEWED', 'RESOLVED', 'DISMISSED')",
            name="finding_status",
        ),
        sa.CheckConstraint(
            "severity IN ('INFO', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="finding_severity",
        ),
        sa.CheckConstraint("confidence IN ('LOW', 'MEDIUM', 'HIGH')", name="finding_confidence"),
        sa.ForeignKeyConstraint(
            ["correlation_match_id"], ["correlation_matches.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["correlation_run_id"], ["correlation_runs.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("correlation_match_id"),
        sa.UniqueConstraint("deterministic_key"),
    )
    op.create_index("ix_findings_case_id", "findings", ["case_id"])
    op.create_index("ix_findings_run_id", "findings", ["correlation_run_id"])
    op.create_index("ix_findings_type", "findings", ["finding_type"])
    op.create_index("ix_findings_status", "findings", ["status"])
    op.create_index("ix_findings_severity", "findings", ["severity"])
    op.create_index("ix_findings_confidence", "findings", ["confidence"])
    op.create_index("ix_findings_rule", "findings", ["rule_id", "rule_version"])
    op.create_index("ix_findings_created_at", "findings", ["created_at"])


def downgrade() -> None:
    for index in (
        "ix_findings_created_at",
        "ix_findings_rule",
        "ix_findings_confidence",
        "ix_findings_severity",
        "ix_findings_status",
        "ix_findings_type",
        "ix_findings_run_id",
        "ix_findings_case_id",
    ):
        op.drop_index(index, table_name="findings")
    op.drop_table("findings")
    op.drop_index("ix_correlation_match_events_event_id", table_name="correlation_match_events")
    op.drop_index("ix_correlation_match_events_match_id", table_name="correlation_match_events")
    op.drop_table("correlation_match_events")
    for index in (
        "ix_correlation_matches_created_at",
        "ix_correlation_matches_rule",
        "ix_correlation_matches_run_id",
        "ix_correlation_matches_case_id",
    ):
        op.drop_index(index, table_name="correlation_matches")
    op.drop_table("correlation_matches")
    for index in (
        "ix_correlation_runs_created_at",
        "ix_correlation_runs_status",
        "ix_correlation_runs_case_id",
    ):
        op.drop_index(index, table_name="correlation_runs")
    op.drop_table("correlation_runs")
