"""add document summary

Revision ID: c7d4a1f0b2e3
Revises: 9f2b7c1d4e11
Create Date: 2026-03-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c7d4a1f0b2e3"
down_revision: Union[str, None] = "9f2b7c1d4e11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("summary", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "summary")
