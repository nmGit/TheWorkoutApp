"""add default rep range to user settings

Revision ID: g4d7a1e9c2b5
Revises: f3c8b2a6d9e1
"""

import sqlalchemy as sa
from alembic import op

revision = "g4d7a1e9c2b5"
down_revision = "f3c8b2a6d9e1"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("user_settings") as batch:
        batch.add_column(sa.Column("default_rep_range", sa.String(length=12), nullable=False, server_default="8-12"))


def downgrade():
    with op.batch_alter_table("user_settings") as batch:
        batch.drop_column("default_rep_range")
