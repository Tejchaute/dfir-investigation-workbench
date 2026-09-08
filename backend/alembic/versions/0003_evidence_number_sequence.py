"""Add concurrency-safe evidence number sequence.

Revision ID: 0003_evidence_number_sequence
Revises: 0002_case_number_sequence
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003_evidence_number_sequence"
down_revision: str | None = "0002_case_number_sequence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE evidence_number_seq START WITH 1 INCREMENT BY 1 NO CYCLE")


def downgrade() -> None:
    op.execute("DROP SEQUENCE evidence_number_seq")
