"""Add enhanced food knowledge base tables

Revision ID: 006_enhanced_food_kb
Revises: 005_add_diet_plans
Create Date: 2025-11-08

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '006_enhanced_food_kb'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade():
    # Create food_dosha_effects table
    op.create_table(
        'food_dosha_effects',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('food_id', sa.Integer(), nullable=False),
        sa.Column('dosha_type', sa.String(length=20), nullable=False),
        sa.Column('effect', sa.String(length=20), nullable=False),
        sa.Column('intensity', sa.Integer(), server_default='1'),
        sa.Column('notes', sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(['food_id'], ['food_items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('food_id', 'dosha_type', name='unique_food_dosha')
    )
    op.create_index('idx_food_dosha_food_id', 'food_dosha_effects', ['food_id'])
    op.create_index('idx_food_dosha_type', 'food_dosha_effects', ['dosha_type', 'effect'])
    
    # Create food_disease_relations table
    op.create_table(
        'food_disease_relations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('food_id', sa.Integer(), nullable=False),
        sa.Column('disease_condition', sa.String(length=100), nullable=False),
        sa.Column('relationship', sa.String(length=20), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('severity', sa.Integer(), server_default='1'),
        sa.ForeignKeyConstraint(['food_id'], ['food_items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('food_id', 'disease_condition', name='unique_food_disease')
    )
    op.create_index('idx_food_disease_food_id', 'food_disease_relations', ['food_id'])
    op.create_index('idx_disease_condition', 'food_disease_relations', ['disease_condition', 'relationship'])
    
    # Create food_allergens table
    op.create_table(
        'food_allergens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('food_id', sa.Integer(), nullable=False),
        sa.Column('allergen', sa.String(length=100), nullable=False),
        sa.Column('allergen_category', sa.String(length=50), nullable=True),
        sa.Column('severity', sa.String(length=20), server_default='major'),
        sa.ForeignKeyConstraint(['food_id'], ['food_items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('food_id', 'allergen', name='unique_food_allergen')
    )
    op.create_index('idx_food_allergen_food_id', 'food_allergens', ['food_id'])
    op.create_index('idx_allergen', 'food_allergens', ['allergen'])
    
    # Create food_goal_scores table
    op.create_table(
        'food_goal_scores',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('food_id', sa.Integer(), nullable=False),
        sa.Column('health_goal', sa.String(length=100), nullable=False),
        sa.Column('score', sa.Integer(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['food_id'], ['food_items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('food_id', 'health_goal', name='unique_food_goal')
    )
    op.create_index('idx_food_goal_food_id', 'food_goal_scores', ['food_id'])
    op.create_index('idx_health_goal', 'food_goal_scores', ['health_goal', 'score'])
    
    # Add new columns to food_items for enhanced scoring
    op.add_column('food_items', sa.Column('glycemic_index', sa.Integer(), nullable=True))
    op.add_column('food_items', sa.Column('glycemic_load', sa.Float(), nullable=True))
    op.add_column('food_items', sa.Column('fiber_g', sa.Float(), nullable=True))
    op.add_column('food_items', sa.Column('overall_health_score', sa.Integer(), server_default='50'))
    op.add_column('food_items', sa.Column('nutrient_density_score', sa.Integer(), server_default='50'))
    op.add_column('food_items', sa.Column('season', sa.String(length=50), nullable=True))
    op.add_column('food_items', sa.Column('rasa', sa.String(length=100), nullable=True))
    op.add_column('food_items', sa.Column('virya', sa.String(length=50), nullable=True))


def downgrade():
    # Drop new columns from food_items
    op.drop_column('food_items', 'virya')
    op.drop_column('food_items', 'rasa')
    op.drop_column('food_items', 'season')
    op.drop_column('food_items', 'nutrient_density_score')
    op.drop_column('food_items', 'overall_health_score')
    op.drop_column('food_items', 'fiber_g')
    op.drop_column('food_items', 'glycemic_load')
    op.drop_column('food_items', 'glycemic_index')
    
    # Drop new tables
    op.drop_table('food_goal_scores')
    op.drop_table('food_allergens')
    op.drop_table('food_disease_relations')
    op.drop_table('food_dosha_effects')

