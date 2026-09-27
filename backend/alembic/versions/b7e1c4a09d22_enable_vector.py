"""enable vector extension

Revision ID: b7e1c4a09d22
Revises:
Create Date: 2026-09-27

"""

from alembic import op

revision = "b7e1c4a09d22"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS vector")
