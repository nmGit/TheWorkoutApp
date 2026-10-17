"""add planned_progression_active to workout sets

Revision ID: k9c2f7a4e1b8
Revises: j7a0d5e3c9f4
"""

import sqlalchemy as sa
from alembic import op

revision = "k9c2f7a4e1b8"
down_revision = "j7a0d5e3c9f4"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("workout_sets") as batch:
        batch.add_column(
            sa.Column("planned_progression_active", sa.Boolean(), nullable=False, server_default=sa.false())
        )


def downgrade():
    with op.batch_alter_table("workout_sets") as batch:
        batch.drop_column("planned_progression_active")
