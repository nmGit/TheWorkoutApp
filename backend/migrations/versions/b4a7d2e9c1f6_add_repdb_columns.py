"""add RepDB-sourced columns, primary_muscles and aliases to exercise_templates

Revision ID: b4a7d2e9c1f6
Revises: e7f1b4a9d6c3
Create Date: 2026-10-03 11:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b4a7d2e9c1f6'
down_revision = 'e7f1b4a9d6c3'
branch_labels = None
depends_on = None


def upgrade():
    # Plain nullable ADD COLUMNs: SQLite supports these without a table
    # rebuild. The unique constraint on repdb_id is a separate unique index
    # since SQLite can't ADD COLUMN ... UNIQUE.
    op.add_column('exercise_templates', sa.Column('repdb_id', sa.String(length=64), nullable=True))
    op.add_column('exercise_templates', sa.Column('repdb_images', sa.JSON(), nullable=True))
    op.add_column('exercise_templates', sa.Column('primary_muscles', sa.JSON(), nullable=True))
    op.add_column('exercise_templates', sa.Column('tips', sa.JSON(), nullable=True))
    op.add_column('exercise_templates', sa.Column('difficulty', sa.String(length=16), nullable=True))
    op.add_column('exercise_templates', sa.Column('mechanic', sa.String(length=16), nullable=True))
    op.add_column('exercise_templates', sa.Column('aliases', sa.JSON(), nullable=True))
    op.create_index('uq_exercise_templates_repdb_id', 'exercise_templates', ['repdb_id'], unique=True)


def downgrade():
    op.drop_index('uq_exercise_templates_repdb_id', table_name='exercise_templates')
    with op.batch_alter_table('exercise_templates', schema=None) as batch_op:
        batch_op.drop_column('aliases')
        batch_op.drop_column('mechanic')
        batch_op.drop_column('difficulty')
        batch_op.drop_column('tips')
        batch_op.drop_column('primary_muscles')
        batch_op.drop_column('repdb_images')
        batch_op.drop_column('repdb_id')
