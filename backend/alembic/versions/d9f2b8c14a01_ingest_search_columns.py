"""ingest: document updated_at, chunk uniqueness, full-text column

Revision ID: d9f2b8c14a01
Revises: c4d8a1e07f33
Create Date: 2026-09-29

"""

import sqlalchemy as sa
from alembic import op

revision = "d9f2b8c14a01"
down_revision = "c4d8a1e07f33"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_unique_constraint(
        "uq_chunks_document_id_chunk_index",
        "chunks",
        ["document_id", "chunk_index"],
    )
    op.execute(
        """
        ALTER TABLE chunks
        ADD COLUMN text_search tsvector
        GENERATED ALWAYS AS (to_tsvector('english', text)) STORED
        """
    )
    op.create_index(
        "ix_chunks_text_search",
        "chunks",
        ["text_search"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_chunks_text_search", table_name="chunks")
    op.drop_column("chunks", "text_search")
    op.drop_constraint("uq_chunks_document_id_chunk_index", "chunks", type_="unique")
    op.drop_column("documents", "updated_at")
