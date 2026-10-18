"""add superset_group to template and workout exercises

Revision ID: j7a0d5e3c9f4
Revises: i6f9c4d1b8e2
"""

import sqlalchemy as sa
from alembic import op

revision = "j7a0d5e3c9f4"
down_revision = "i6f9c4d1b8e2"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("template_exercises") as batch:
        batch.add_column(sa.Column("superset_group", sa.Integer(), nullable=True))
    with op.batch_alter_table("workout_exercises") as batch:
        batch.add_column(sa.Column("superset_group", sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table("workout_exercises") as batch:
        batch.drop_column("superset_group")
    with op.batch_alter_table("template_exercises") as batch:
        batch.drop_column("superset_group")
