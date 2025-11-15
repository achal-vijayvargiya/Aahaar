"""Add nutrition knowledge base table

Revision ID: 001
Revises: 
Create Date: 2025-10-30 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Create nutrition_knowledge table with full-text search support"""
    
    # Create the nutrition_knowledge table
    op.create_table(
        'nutrition_knowledge',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('disorder_name', sa.String(length=200), nullable=False),
        sa.Column('definition_etiology', sa.Text(), nullable=True),
        sa.Column('clinical_goals', sa.Text(), nullable=True),
        sa.Column('mnt_macronutrients', sa.Text(), nullable=True),
        sa.Column('mnt_micronutrients', sa.Text(), nullable=True),
        sa.Column('mnt_fluids_electrolytes', sa.Text(), nullable=True),
        sa.Column('mnt_special_notes', sa.Text(), nullable=True),
        sa.Column('ayurvedic_view', sa.Text(), nullable=True),
        sa.Column('dosha_dominance', sa.String(length=100), nullable=True),
        sa.Column('lifestyle_yogic_guidance', sa.Text(), nullable=True),
        sa.Column('healing_affirmation', sa.Text(), nullable=True),
        sa.Column('search_vector', postgresql.TSVECTOR(), nullable=True),
        sa.Column('embedding_id', sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for better query performance
    op.create_index('ix_nutrition_knowledge_id', 'nutrition_knowledge', ['id'], unique=False)
    op.create_index('ix_nutrition_knowledge_category', 'nutrition_knowledge', ['category'], unique=False)
    op.create_index('ix_nutrition_knowledge_disorder_name', 'nutrition_knowledge', ['disorder_name'], unique=False)
    op.create_index('ix_nutrition_knowledge_dosha_dominance', 'nutrition_knowledge', ['dosha_dominance'], unique=False)
    op.create_index('ix_nutrition_knowledge_embedding_id', 'nutrition_knowledge', ['embedding_id'], unique=True)
    
    # Create composite index for category + disorder_name
    op.create_index('idx_category_disorder', 'nutrition_knowledge', ['category', 'disorder_name'], unique=False)
    
    # Create GIN index for full-text search
    op.create_index(
        'idx_nutrition_search',
        'nutrition_knowledge',
        ['search_vector'],
        unique=False,
        postgresql_using='gin'
    )


def downgrade():
    """Drop nutrition_knowledge table and all indexes"""
    
    # Drop indexes first
    op.drop_index('idx_nutrition_search', table_name='nutrition_knowledge', postgresql_using='gin')
    op.drop_index('idx_category_disorder', table_name='nutrition_knowledge')
    op.drop_index('ix_nutrition_knowledge_embedding_id', table_name='nutrition_knowledge')
    op.drop_index('ix_nutrition_knowledge_dosha_dominance', table_name='nutrition_knowledge')
    op.drop_index('ix_nutrition_knowledge_disorder_name', table_name='nutrition_knowledge')
    op.drop_index('ix_nutrition_knowledge_category', table_name='nutrition_knowledge')
    op.drop_index('ix_nutrition_knowledge_id', table_name='nutrition_knowledge')
    
    # Drop the table
    op.drop_table('nutrition_knowledge')

