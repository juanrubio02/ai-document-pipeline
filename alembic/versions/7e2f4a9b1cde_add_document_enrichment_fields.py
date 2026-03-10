"""add document enrichment fields

Revision ID: 7e2f4a9b1cde
Revises: c7d4a1f0b2e3
Create Date: 2026-03-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7e2f4a9b1cde"
down_revision: Union[str, None] = "c7d4a1f0b2e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("document_type", sa.String(length=64), nullable=True))
    op.add_column("documents", sa.Column("keywords", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "keywords")
    op.drop_column("documents", "document_type")
