"""add progression settings and load steps to user settings

Revision ID: f3c8b2a6d9e1
Revises: e2a9c4d1b7f0
"""

import sqlalchemy as sa
from alembic import op

revision = "f3c8b2a6d9e1"
down_revision = "e2a9c4d1b7f0"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("user_settings") as batch:
        batch.add_column(sa.Column("progression_method", sa.String(length=6), nullable=False, server_default="double"))
        batch.add_column(sa.Column("experience", sa.String(length=12), nullable=False, server_default="intermediate"))
        batch.add_column(sa.Column("load_step_lb", sa.Float(), nullable=False, server_default="5.0"))
        batch.add_column(sa.Column("load_step_kg", sa.Float(), nullable=False, server_default="2.5"))


def downgrade():
    with op.batch_alter_table("user_settings") as batch:
        batch.drop_column("load_step_kg")
        batch.drop_column("load_step_lb")
        batch.drop_column("experience")
        batch.drop_column("progression_method")
