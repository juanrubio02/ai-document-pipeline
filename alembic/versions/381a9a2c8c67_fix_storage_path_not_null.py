"""fix storage_path not null

Revision ID: 381a9a2c8c67
Revises: e3f529450c35
Create Date: 2026-03-05 08:51:44.306427

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "381a9a2c8c67"
down_revision: Union[str, None] = "e3f529450c35"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE documents SET storage_path = '' WHERE storage_path IS NULL")
    op.execute("ALTER TABLE documents ALTER COLUMN storage_path SET NOT NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE documents ALTER COLUMN storage_path DROP NOT NULL")
