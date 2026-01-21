"""add_meal_structure_table

Revision ID: 9a92a6d3940a
Revises: 011_meal_structure_fields
Create Date: 2025-12-18 21:39:22.807550

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '9a92a6d3940a'
down_revision: Union[str, None] = '011_meal_structure_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create platform_meal_structures table
    op.create_table(
        'platform_meal_structures',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assessment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('meal_count', sa.Integer(), nullable=False),
        sa.Column('meals', postgresql.JSONB(), nullable=False),
        sa.Column('timing_windows', postgresql.JSONB(), nullable=False),
        sa.Column('calorie_split', postgresql.JSONB(), nullable=False),
        sa.Column('protein_split', postgresql.JSONB(), nullable=False),
        sa.Column('macro_guardrails', postgresql.JSONB(), nullable=True),
        sa.Column('flags', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['assessment_id'], ['platform_assessments.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('assessment_id')
    )
    op.create_index('ix_platform_meal_structures_id', 'platform_meal_structures', ['id'], unique=False)
    op.create_index('ix_platform_meal_structures_assessment_id', 'platform_meal_structures', ['assessment_id'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_platform_meal_structures_assessment_id', table_name='platform_meal_structures')
    op.drop_index('ix_platform_meal_structures_id', table_name='platform_meal_structures')
    op.drop_table('platform_meal_structures')

