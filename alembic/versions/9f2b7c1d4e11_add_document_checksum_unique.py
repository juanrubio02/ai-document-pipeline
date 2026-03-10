"""add document checksum unique

Revision ID: 9f2b7c1d4e11
Revises: 381a9a2c8c67
Create Date: 2026-03-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9f2b7c1d4e11"
down_revision: Union[str, None] = "381a9a2c8c67"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("checksum", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_documents_checksum_unique_not_null",
        "documents",
        ["checksum"],
        unique=True,
        postgresql_where=sa.text("checksum IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_documents_checksum_unique_not_null", table_name="documents")
    op.drop_column("documents", "checksum")
