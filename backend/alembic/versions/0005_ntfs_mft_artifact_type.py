"""Add the controlled NTFS_MFT artifact type.

Revision ID: 0005_ntfs_mft_type
Revises: 0004_parser_framework
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005_ntfs_mft_type"
down_revision: str | None = "0004_parser_framework"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("artifact_type", "artifacts", type_="check")
    op.create_check_constraint(
        "artifact_type",
        "artifacts",
        "artifact_type IN ('REFERENCE', 'EVTX', 'REGISTRY', 'PREFETCH', 'LNK', 'NTFS', 'NTFS_MFT')",
    )


def downgrade() -> None:
    op.execute("UPDATE artifacts SET artifact_type = 'NTFS' WHERE artifact_type = 'NTFS_MFT'")
    op.drop_constraint("artifact_type", "artifacts", type_="check")
    op.create_check_constraint(
        "artifact_type",
        "artifacts",
        "artifact_type IN ('REFERENCE', 'EVTX', 'REGISTRY', 'PREFETCH', 'LNK', 'NTFS')",
    )
