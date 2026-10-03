"""add exercise_template columns for the Exercise/ExerciseTemplate merge, retarget FKs, add WorkoutSet.rest_seconds

Revision ID: c3d9a1f5e8b2
Revises: 8f2b6c1a9d3e
Create Date: 2026-09-27 21:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c3d9a1f5e8b2'
down_revision = '8f2b6c1a9d3e'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('exercise_templates', schema=None) as batch_op:
        batch_op.add_column(sa.Column('muscle_group_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('equipment_raw', sa.String(length=64), nullable=True))
        batch_op.add_column(
            sa.Column(
                'tracking_type',
                sa.Enum(
                    'weight_reps', 'bodyweight_reps', 'time', 'cardio',
                    name='tracking_type', native_enum=False,
                ),
                nullable=True,
            )
        )
        batch_op.add_column(sa.Column('notes', sa.Text(), nullable=True))
        batch_op.create_foreign_key(
            'fk_exercise_templates_muscle_group_id_muscle_groups',
            'muscle_groups',
            ['muscle_group_id'],
            ['id'],
        )

    # exercise_id currently references exercises.id (no explicit constraint
    # name -- see migrations/versions/55f39fee44ca_initial_schema.py). SQLite
    # batch mode carries forward reflected constraints unless the rebuilt
    # table's definition omits them, so `copy_from` explicitly redefines
    # each table without that FK rather than trying to drop-by-name a
    # constraint that was never named.
    template_exercises_def = sa.Table(
        'template_exercises',
        sa.MetaData(),
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('exercise_id', sa.Integer(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('target_sets', sa.Integer(), nullable=True),
        sa.Column('target_reps', sa.String(length=32), nullable=True),
        sa.Column('target_weight', sa.Numeric(precision=8, scale=4), nullable=True),
        sa.ForeignKeyConstraint(['template_id'], ['workout_templates.id'], ondelete='CASCADE'),
    )
    with op.batch_alter_table(
        'template_exercises', schema=None, recreate='always', copy_from=template_exercises_def
    ) as batch_op:
        batch_op.create_foreign_key(
            'fk_template_exercises_exercise_id_exercise_templates',
            'exercise_templates',
            ['exercise_id'],
            ['id'],
        )

    workout_exercises_def = sa.Table(
        'workout_exercises',
        sa.MetaData(),
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('workout_id', sa.Integer(), nullable=False),
        sa.Column('exercise_id', sa.Integer(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['workout_id'], ['workouts.id'], ondelete='CASCADE'),
    )
    with op.batch_alter_table(
        'workout_exercises', schema=None, recreate='always', copy_from=workout_exercises_def
    ) as batch_op:
        batch_op.create_foreign_key(
            'fk_workout_exercises_exercise_id_exercise_templates',
            'exercise_templates',
            ['exercise_id'],
            ['id'],
        )

    with op.batch_alter_table('workout_sets', schema=None) as batch_op:
        batch_op.add_column(sa.Column('rest_seconds', sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table('workout_sets', schema=None) as batch_op:
        batch_op.drop_column('rest_seconds')

    workout_exercises_def = sa.Table(
        'workout_exercises',
        sa.MetaData(),
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('workout_id', sa.Integer(), nullable=False),
        sa.Column('exercise_id', sa.Integer(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['workout_id'], ['workouts.id'], ondelete='CASCADE'),
    )
    with op.batch_alter_table(
        'workout_exercises', schema=None, recreate='always', copy_from=workout_exercises_def
    ) as batch_op:
        batch_op.create_foreign_key(None, 'exercises', ['exercise_id'], ['id'])

    template_exercises_def = sa.Table(
        'template_exercises',
        sa.MetaData(),
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('template_id', sa.Integer(), nullable=False),
        sa.Column('exercise_id', sa.Integer(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('target_sets', sa.Integer(), nullable=True),
        sa.Column('target_reps', sa.String(length=32), nullable=True),
        sa.Column('target_weight', sa.Numeric(precision=8, scale=4), nullable=True),
        sa.ForeignKeyConstraint(['template_id'], ['workout_templates.id'], ondelete='CASCADE'),
    )
    with op.batch_alter_table(
        'template_exercises', schema=None, recreate='always', copy_from=template_exercises_def
    ) as batch_op:
        batch_op.create_foreign_key(None, 'exercises', ['exercise_id'], ['id'])

    with op.batch_alter_table('exercise_templates', schema=None) as batch_op:
        batch_op.drop_constraint(
            'fk_exercise_templates_muscle_group_id_muscle_groups', type_='foreignkey'
        )
        batch_op.drop_column('notes')
        batch_op.drop_column('tracking_type')
        batch_op.drop_column('equipment_raw')
        batch_op.drop_column('muscle_group_id')
