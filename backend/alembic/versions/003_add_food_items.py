"""Add food items table

Revision ID: 003
Revises: 002
Create Date: 2025-11-02 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003_food'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    """Create food_items table"""
    
    op.create_table(
        'food_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('food_name', sa.String(length=200), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('serving_size', sa.String(length=50), nullable=True),
        sa.Column('region', sa.String(length=100), nullable=True),
        sa.Column('energy_kcal', sa.Float(), nullable=True),
        sa.Column('protein_g', sa.Float(), nullable=True),
        sa.Column('fat_g', sa.Float(), nullable=True),
        sa.Column('carbs_g', sa.Float(), nullable=True),
        sa.Column('key_micronutrients', sa.Text(), nullable=True),
        sa.Column('dosha_impact', sa.String(length=100), nullable=True),
        sa.Column('satvik_rajasik_tamasik', sa.String(length=50), nullable=True),
        sa.Column('gut_biotic_value', sa.String(length=50), nullable=True),
        sa.Column('search_vector', postgresql.TSVECTOR(), nullable=True),
        sa.Column('embedding_id', sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_food_items_id', 'food_items', ['id'], unique=False)
    op.create_index('ix_food_items_food_name', 'food_items', ['food_name'], unique=False)
    op.create_index('ix_food_items_category', 'food_items', ['category'], unique=False)
    op.create_index('ix_food_items_protein_g', 'food_items', ['protein_g'], unique=False)
    op.create_index('ix_food_items_dosha_impact', 'food_items', ['dosha_impact'], unique=False)
    op.create_index('ix_food_items_satvik_rajasik_tamasik', 'food_items', ['satvik_rajasik_tamasik'], unique=False)
    op.create_index('ix_food_items_embedding_id', 'food_items', ['embedding_id'], unique=True)
    
    # Composite indexes
    op.create_index('idx_category_dosha', 'food_items', ['category', 'dosha_impact'], unique=False)
    op.create_index('idx_nutrition', 'food_items', ['protein_g', 'carbs_g', 'fat_g'], unique=False)
    
    # GIN index for full-text search
    op.create_index(
        'idx_food_search',
        'food_items',
        ['search_vector'],
        unique=False,
        postgresql_using='gin'
    )


def downgrade():
    """Drop food_items table"""
    
    # Drop indexes
    op.drop_index('idx_food_search', table_name='food_items', postgresql_using='gin')
    op.drop_index('idx_nutrition', table_name='food_items')
    op.drop_index('idx_category_dosha', table_name='food_items')
    op.drop_index('ix_food_items_embedding_id', table_name='food_items')
    op.drop_index('ix_food_items_satvik_rajasik_tamasik', table_name='food_items')
    op.drop_index('ix_food_items_dosha_impact', table_name='food_items')
    op.drop_index('ix_food_items_protein_g', table_name='food_items')
    op.drop_index('ix_food_items_category', table_name='food_items')
    op.drop_index('ix_food_items_food_name', table_name='food_items')
    op.drop_index('ix_food_items_id', table_name='food_items')
    
    # Drop table
    op.drop_table('food_items')

