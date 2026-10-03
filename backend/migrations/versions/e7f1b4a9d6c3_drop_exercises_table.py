"""drop the exercises table (superseded by exercise_templates)

Revision ID: e7f1b4a9d6c3
Revises: c3d9a1f5e8b2
Create Date: 2026-09-27 22:15:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'e7f1b4a9d6c3'
down_revision = 'c3d9a1f5e8b2'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table('exercises')


def downgrade():
    raise RuntimeError(
        "Irreversible past this point -- the exercises table's data is gone and "
        "workout_exercises/template_exercises have already been rewritten to "
        "reference exercise_templates.id instead. Restore data/workout.db from "
        "the pre-merge backup (data/workout.db.pre-exercise-template-merge-backup) "
        "instead of trying to downgrade."
    )
