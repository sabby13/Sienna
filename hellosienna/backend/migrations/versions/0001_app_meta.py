"""0001 app_meta (M0 foundation table only)

Creates ONLY app_meta. Domain tables (person/conversation/message/... ) are
introduced by later migrations at M1+ per the frozen contract — see M0 non-goals.

Revision ID: 0001_app_meta
Revises:
Create Date: 2026-09-07
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_app_meta"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_meta",
        sa.Column("key", sa.Text(), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("app_meta")
