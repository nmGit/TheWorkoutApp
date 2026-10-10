"""add warm-up and drop set counts to template exercises

Revision ID: e2a9c4d1b7f0
Revises: d5e1c8a2f7b3
"""

import sqlalchemy as sa
from alembic import op

revision = "e2a9c4d1b7f0"
down_revision = "d5e1c8a2f7b3"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("template_exercises") as batch:
        batch.add_column(sa.Column("warmup_sets", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("drop_sets", sa.Integer(), nullable=False, server_default="0"))


def downgrade():
    with op.batch_alter_table("template_exercises") as batch:
        batch.drop_column("drop_sets")
        batch.drop_column("warmup_sets")
