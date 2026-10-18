"""split catalog data from user data: custom_exercise_templates, catalog_exercise_notes,
exercise/custom_exercise_id on workout_exercises & template_exercises

Revision ID: l0d3a8f5c2e9
Revises: k9c2f7a4e1b8

Schema-only. The catalog tables (exercise_templates, exercise_muscles, muscles, muscle_groups)
are NOT touched or dropped here -- this is the "default" (user) bind's migration, and those
tables are moving to the new "catalog" bind, a separate database file. Moving their data and
severing the old exercise_id's dependence on them is a one-off script
(scripts/split_catalog_database.py), run once between this migration and the one that follows
it (which drops the now-redundant catalog tables from this database, once that script has
verified they're no longer needed here). See docs/source/data_model.rst "Database split".
"""

import sqlalchemy as sa
from alembic import op

revision = "l0d3a8f5c2e9"
down_revision = "k9c2f7a4e1b8"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "custom_exercise_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("equipment", sa.String(length=64), nullable=True),
        sa.Column(
            "tracking_type",
            sa.Enum("weight_reps", "bodyweight_reps", "time", "cardio", name="custom_tracking_type", native_enum=False),
            nullable=True,
        ),
        sa.Column("muscle_group_id", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("primary_muscles", sa.JSON(), nullable=True),
        sa.Column("secondary_muscles", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "catalog_exercise_notes",
        sa.Column("exercise_id", sa.Integer(), primary_key=True),
        sa.Column("notes", sa.Text(), nullable=False),
    )

    for table in ("workout_exercises", "template_exercises"):
        with op.batch_alter_table(table) as batch:
            # Drop the old FK to exercise_templates -- that table is leaving this database for
            # the catalog one, and the model no longer declares this as an enforced FK (see
            # models/exercise_reference.py). Dropping it now, while the table's already being
            # recreated for the other changes, avoids a second recreate later just for this.
            batch.drop_constraint(f"fk_{table}_exercise_id_exercise_templates", type_="foreignkey")
            batch.alter_column("exercise_id", existing_type=sa.Integer(), nullable=True)
            batch.add_column(sa.Column("custom_exercise_id", sa.Integer(), nullable=True))
            batch.create_foreign_key(
                f"fk_{table}_custom_exercise_id", "custom_exercise_templates", ["custom_exercise_id"], ["id"]
            )
            batch.create_check_constraint(
                f"ck_{table}_exactly_one_exercise",
                "(exercise_id IS NULL) != (custom_exercise_id IS NULL)",
            )


def downgrade():
    # Not a full inverse -- the dropped exercise_templates FK isn't recreated (that table may
    # already be gone from this database by the time anyone downgrades), only the parts of this
    # migration that are safe to unwind on their own.
    for table in ("workout_exercises", "template_exercises"):
        with op.batch_alter_table(table) as batch:
            batch.drop_constraint(f"ck_{table}_exactly_one_exercise", type_="check")
            batch.drop_constraint(f"fk_{table}_custom_exercise_id", type_="foreignkey")
            batch.drop_column("custom_exercise_id")
            batch.alter_column("exercise_id", existing_type=sa.Integer(), nullable=False)
    op.drop_table("catalog_exercise_notes")
    op.drop_table("custom_exercise_templates")
