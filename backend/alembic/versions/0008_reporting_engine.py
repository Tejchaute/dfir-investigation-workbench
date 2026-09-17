"""Add immutable report metadata and rendered artifact records.

Revision ID: 0008_reporting_engine
Revises: 0007_correlation_findings
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0008_reporting_engine"
down_revision: str | None = "0007_correlation_findings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_type", sa.String(length=29), nullable=False),
        sa.Column("report_version", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=9), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generated_by", sa.String(length=255), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("snapshot_path", sa.String(length=500), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("report_type IN ('FORENSIC_INVESTIGATION_REPORT')", name="report_type"),
        sa.CheckConstraint("status IN ('GENERATED', 'FAILED')", name="report_status"),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reports_case_id", "reports", ["case_id"])
    op.create_index("ix_reports_created_at", "reports", ["created_at"])
    op.create_table(
        "report_artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("format", sa.String(length=4), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("format IN ('json', 'html', 'pdf')", name="report_format"),
        sa.CheckConstraint("size_bytes >= 0", name="ck_report_artifact_size_nonnegative"),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_path"),
    )
    op.create_index("ix_report_artifacts_report_id", "report_artifacts", ["report_id"])


def downgrade() -> None:
    op.drop_index("ix_report_artifacts_report_id", table_name="report_artifacts")
    op.drop_table("report_artifacts")
    op.drop_index("ix_reports_created_at", table_name="reports")
    op.drop_index("ix_reports_case_id", table_name="reports")
    op.drop_table("reports")
