"""add_energy_weight_macro_intent_to_meal_structure

Revision ID: ab6f352019a6
Revises: e1b0caed6dae
Create Date: 2026-01-14 20:04:15.228598

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'ab6f352019a6'
down_revision: Union[str, None] = 'e1b0caed6dae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns for nutrition-agnostic meal structure
    op.add_column('platform_meal_structures', 
                  sa.Column('energy_weight', postgresql.JSONB(), nullable=True))
    op.add_column('platform_meal_structures', 
                  sa.Column('macro_intent', postgresql.JSONB(), nullable=True))
    
    # Make legacy columns nullable (they're deprecated but kept for backward compatibility)
    op.alter_column('platform_meal_structures', 'calorie_split',
                    existing_type=postgresql.JSONB(),
                    nullable=True)
    op.alter_column('platform_meal_structures', 'protein_split',
                    existing_type=postgresql.JSONB(),
                    nullable=True)


def downgrade() -> None:
    # Remove new columns (check if they exist first)
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('platform_meal_structures')]
    
    if 'macro_intent' in columns:
        op.drop_column('platform_meal_structures', 'macro_intent')
    if 'energy_weight' in columns:
        op.drop_column('platform_meal_structures', 'energy_weight')
    
    # Restore legacy columns to NOT NULL (if needed)
    if 'protein_split' in columns:
        op.alter_column('platform_meal_structures', 'protein_split',
                        existing_type=postgresql.JSONB(),
                        nullable=False)
    if 'calorie_split' in columns:
        op.alter_column('platform_meal_structures', 'calorie_split',
                        existing_type=postgresql.JSONB(),
                        nullable=False)

