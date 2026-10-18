"""drop the old catalog tables from the user database, now that scripts/split_catalog_database.py
has moved their data into the separate catalog database

Revision ID: m1e4b9a6d3f0
Revises: l0d3a8f5c2e9

Only safe to run after scripts/split_catalog_database.py --apply has been run and its catalog
database verified -- this drops the source data it read from. See that script and
docs/source/data_model.rst "Database split".
"""

from alembic import op

revision = "m1e4b9a6d3f0"
down_revision = "l0d3a8f5c2e9"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table("exercise_muscles")
    op.drop_table("exercise_templates")
    op.drop_table("muscles")
    op.drop_table("muscle_groups")


def downgrade():
    raise NotImplementedError(
        "Irreversible: downgrading would need the catalog data copied back in from the "
        "catalog database, which this migration framework doesn't manage. Restore from a "
        "backup taken before upgrading instead."
    )
