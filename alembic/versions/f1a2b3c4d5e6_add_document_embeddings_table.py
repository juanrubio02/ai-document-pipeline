"""add document embeddings table

Revision ID: f1a2b3c4d5e6
Revises: 7e2f4a9b1cde
Create Date: 2026-03-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, None] = "7e2f4a9b1cde"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "document_embeddings",
        sa.Column("document_id", sa.String(length=32), nullable=False),
        sa.Column("embedding", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.document_id"]),
        sa.PrimaryKeyConstraint("document_id"),
    )


def downgrade() -> None:
    op.drop_table("document_embeddings")
