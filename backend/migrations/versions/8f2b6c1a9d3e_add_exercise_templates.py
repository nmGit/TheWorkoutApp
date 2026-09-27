"""add exercise_templates table and exercises.template_id

Revision ID: 8f2b6c1a9d3e
Revises: 1a01854fdc3a
Create Date: 2026-09-27 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8f2b6c1a9d3e'
down_revision = '1a01854fdc3a'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'exercise_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('external_id', sa.String(length=16), nullable=True),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('category', sa.String(length=64), nullable=True),
        sa.Column('body_part', sa.String(length=64), nullable=True),
        sa.Column('equipment', sa.String(length=64), nullable=True),
        sa.Column('target_muscle', sa.String(length=64), nullable=True),
        sa.Column('muscle_group', sa.String(length=64), nullable=True),
        sa.Column('secondary_muscles', sa.JSON(), nullable=True),
        sa.Column('instructions', sa.Text(), nullable=True),
        sa.Column('instruction_steps', sa.JSON(), nullable=True),
        sa.Column('image_path', sa.String(length=255), nullable=True),
        sa.Column('attribution', sa.String(length=255), nullable=True),
        sa.Column('is_custom', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('external_id'),
    )

    with op.batch_alter_table('exercises', schema=None) as batch_op:
        batch_op.add_column(sa.Column('template_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_exercises_template_id_exercise_templates',
            'exercise_templates',
            ['template_id'],
            ['id'],
        )


def downgrade():
    with op.batch_alter_table('exercises', schema=None) as batch_op:
        batch_op.drop_constraint(
            'fk_exercises_template_id_exercise_templates', type_='foreignkey'
        )
        batch_op.drop_column('template_id')

    op.drop_table('exercise_templates')
