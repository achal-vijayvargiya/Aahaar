"""add_kb_food_modular_tables

Revision ID: e1b0caed6dae
Revises: 9b550b9ca9a9
Create Date: 2025-01-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e1b0caed6dae'
down_revision: Union[str, None] = '9b550b9ca9a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create kb_food_master table
    op.create_table(
        'kb_food_master',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('food_id', sa.String(length=100), nullable=False),
        sa.Column('display_name', sa.String(length=200), nullable=False),
        sa.Column('aliases', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('food_type', sa.String(length=100), nullable=True),
        sa.Column('region', sa.String(length=100), nullable=True),
        sa.Column('diet_type', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('cooking_state', sa.String(length=50), nullable=True),
        sa.Column('common_serving_unit', sa.String(length=50), nullable=True),
        sa.Column('common_serving_size_g', sa.Numeric(10, 2), nullable=True),
        sa.Column('version', sa.String(length=20), nullable=True, server_default='1.0'),
        sa.Column('status', sa.String(length=20), nullable=True, server_default='active'),
        sa.Column('source', sa.String(length=200), nullable=True),
        sa.Column('source_reference', sa.String(length=500), nullable=True),
        sa.Column('last_reviewed', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('food_id')
    )
    op.create_index('idx_food_master_category', 'kb_food_master', ['category'], unique=False)
    op.create_index('idx_food_master_status', 'kb_food_master', ['status'], unique=False)
    op.create_index(op.f('ix_kb_food_master_id'), 'kb_food_master', ['id'], unique=False)
    
    # Create kb_food_nutrition_base table
    op.create_table(
        'kb_food_nutrition_base',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('food_id', sa.String(length=100), nullable=False),
        sa.Column('calories_kcal', sa.Numeric(10, 2), nullable=True),
        sa.Column('macros', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('micros', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('glycemic_properties', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('calorie_density_kcal_per_g', sa.Numeric(10, 4), nullable=True),
        sa.Column('protein_density_g_per_100kcal', sa.Numeric(10, 4), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['food_id'], ['kb_food_master.food_id'], ondelete='CASCADE'),
        sa.UniqueConstraint('food_id')
    )
    op.create_index(op.f('ix_kb_food_nutrition_base_id'), 'kb_food_nutrition_base', ['id'], unique=False)
    
    # Create kb_food_exchange_profile table
    op.create_table(
        'kb_food_exchange_profile',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('food_id', sa.String(length=100), nullable=False),
        sa.Column('exchange_category', sa.String(length=100), nullable=False),
        sa.Column('serving_size_per_exchange_g', sa.Numeric(10, 2), nullable=True),
        sa.Column('exchanges_per_common_serving', sa.Numeric(10, 2), nullable=True),
        sa.Column('notes', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['food_id'], ['kb_food_master.food_id'], ondelete='CASCADE'),
        sa.UniqueConstraint('food_id')
    )
    op.create_index('idx_food_exchange_category', 'kb_food_exchange_profile', ['exchange_category'], unique=False)
    op.create_index(op.f('ix_kb_food_exchange_profile_id'), 'kb_food_exchange_profile', ['id'], unique=False)
    
    # Create kb_food_mnt_profile table
    op.create_table(
        'kb_food_mnt_profile',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('food_id', sa.String(length=100), nullable=False),
        sa.Column('macro_compliance', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('micro_compliance', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('medical_tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('food_exclusion_tags', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('food_inclusion_tags', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('contraindications', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('preferred_conditions', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['food_id'], ['kb_food_master.food_id'], ondelete='CASCADE'),
        sa.UniqueConstraint('food_id')
    )
    op.create_index(op.f('ix_kb_food_mnt_profile_id'), 'kb_food_mnt_profile', ['id'], unique=False)
    
    # Create kb_food_ayurvedic_profile table
    op.create_table(
        'kb_food_ayurvedic_profile',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('food_id', sa.String(length=100), nullable=False),
        sa.Column('dosha_effects', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('guna', sa.String(length=50), nullable=True),
        sa.Column('rasa', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('virya', sa.String(length=50), nullable=True),
        sa.Column('vipaka', sa.String(length=50), nullable=True),
        sa.Column('agni_effect', sa.String(length=50), nullable=True),
        sa.Column('digestive_load', sa.String(length=50), nullable=True),
        sa.Column('food_temperature_preference', sa.String(length=50), nullable=True),
        sa.Column('cooking_method_preference', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('meal_timing_preference', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('season_preference', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['food_id'], ['kb_food_master.food_id'], ondelete='CASCADE'),
        sa.UniqueConstraint('food_id')
    )
    op.create_index(op.f('ix_kb_food_ayurvedic_profile_id'), 'kb_food_ayurvedic_profile', ['id'], unique=False)
    
    # Create kb_food_recipe_profile table
    op.create_table(
        'kb_food_recipe_profile',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('food_id', sa.String(length=100), nullable=False),
        sa.Column('recipe_compatibility', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('retrieval_scoring', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('dietary_properties', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['food_id'], ['kb_food_master.food_id'], ondelete='CASCADE'),
        sa.UniqueConstraint('food_id')
    )
    op.create_index(op.f('ix_kb_food_recipe_profile_id'), 'kb_food_recipe_profile', ['id'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_kb_food_recipe_profile_id'), table_name='kb_food_recipe_profile')
    
    op.drop_index(op.f('ix_kb_food_ayurvedic_profile_id'), table_name='kb_food_ayurvedic_profile')
    
    op.drop_index(op.f('ix_kb_food_mnt_profile_id'), table_name='kb_food_mnt_profile')
    
    op.drop_index(op.f('ix_kb_food_exchange_profile_id'), table_name='kb_food_exchange_profile')
    op.drop_index('idx_food_exchange_category', table_name='kb_food_exchange_profile')
    
    op.drop_index(op.f('ix_kb_food_nutrition_base_id'), table_name='kb_food_nutrition_base')
    
    op.drop_index(op.f('ix_kb_food_master_id'), table_name='kb_food_master')
    op.drop_index('idx_food_master_status', table_name='kb_food_master')
    op.drop_index('idx_food_master_category', table_name='kb_food_master')
    
    # Drop tables (in reverse order due to foreign key constraints)
    op.drop_table('kb_food_recipe_profile')
    op.drop_table('kb_food_ayurvedic_profile')
    op.drop_table('kb_food_mnt_profile')
    op.drop_table('kb_food_exchange_profile')
    op.drop_table('kb_food_nutrition_base')
    op.drop_table('kb_food_master')

