"""add planned_is_progressed to workout sets

Revision ID: i6f9c4d1b8e2
Revises: h5e8b3f0a2c6
"""

import sqlalchemy as sa
from alembic import op

revision = "i6f9c4d1b8e2"
down_revision = "h5e8b3f0a2c6"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("workout_sets") as batch:
        batch.add_column(
            sa.Column("planned_is_progressed", sa.Boolean(), nullable=False, server_default=sa.false())
        )


def downgrade():
    with op.batch_alter_table("workout_sets") as batch:
        batch.drop_column("planned_is_progressed")
