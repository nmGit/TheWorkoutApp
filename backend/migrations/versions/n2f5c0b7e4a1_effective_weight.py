"""add effective_weight to workout sets

Revision ID: n2f5c0b7e4a1
Revises: m1e4b9a6d3f0

Schema only -- backfilling existing rows is a separate one-off script
(scripts/backfill_effective_weight.py), since it needs to read the catalog
database (an exercise's tracking_type) and the body-weight log, not just
add a column. See docs/source/data_model.rst.
"""

import sqlalchemy as sa
from alembic import op

revision = "n2f5c0b7e4a1"
down_revision = "m1e4b9a6d3f0"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("workout_sets") as batch:
        batch.add_column(sa.Column("effective_weight", sa.Numeric(8, 4), nullable=True))


def downgrade():
    with op.batch_alter_table("workout_sets") as batch:
        batch.drop_column("effective_weight")
