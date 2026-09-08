"""Add concurrency-safe case number sequence.

Revision ID: 0002_case_number_sequence
Revises: 0001_phase1_core
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002_case_number_sequence"
down_revision: str | None = "0001_phase1_core"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE case_number_seq START WITH 1 INCREMENT BY 1 NO CYCLE")


def downgrade() -> None:
    op.execute("DROP SEQUENCE case_number_seq")
