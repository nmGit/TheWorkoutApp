"""add planned values to workout sets

Revision ID: h5e8b3f0a2c6
Revises: g4d7a1e9c2b5
"""

import sqlalchemy as sa
from alembic import op

revision = "h5e8b3f0a2c6"
down_revision = "g4d7a1e9c2b5"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("workout_sets") as batch:
        batch.add_column(sa.Column("planned_weight", sa.Numeric(8, 4), nullable=True))
        batch.add_column(sa.Column("planned_weight_unit", sa.String(length=3), nullable=True))
        batch.add_column(sa.Column("planned_reps", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("planned_duration_seconds", sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table("workout_sets") as batch:
        batch.drop_column("planned_duration_seconds")
        batch.drop_column("planned_reps")
        batch.drop_column("planned_weight_unit")
        batch.drop_column("planned_weight")
