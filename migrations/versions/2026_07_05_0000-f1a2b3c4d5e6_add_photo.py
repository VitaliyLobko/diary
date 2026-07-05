"""add photo column to students and teachers

Revision ID: f1a2b3c4d5e6
Revises: b864dccfebce
Create Date: 2026-07-05 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, None] = "b864dccfebce"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("students", sa.Column("photo", sa.String(length=255), nullable=True))
    op.add_column("teachers", sa.Column("photo", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("teachers", "photo")
    op.drop_column("students", "photo")
