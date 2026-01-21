"""add_kb_lab_thresholds_modifier_rules_compatibility

Revision ID: 9b550b9ca9a9
Revises: 9a92a6d3940a
Create Date: 2025-12-20 15:19:08.574713

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '9b550b9ca9a9'
down_revision: Union[str, None] = '9a92a6d3940a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create kb_lab_thresholds table
    op.create_table(
        'kb_lab_thresholds',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('lab_name', sa.String(length=100), nullable=False),
        sa.Column('display_name', sa.String(length=200), nullable=False),
        sa.Column('normal_range', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('abnormal_ranges', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('units', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('conversion_factors', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('source', sa.String(length=200), nullable=True),
        sa.Column('source_reference', sa.String(length=500), nullable=True),
        sa.Column('version', sa.String(length=20), nullable=True, server_default='1.0'),
        sa.Column('status', sa.String(length=20), nullable=True, server_default='active'),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column('last_updated', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('lab_name')
    )
    op.create_index('idx_kb_lab_thresholds_lab_name', 'kb_lab_thresholds', ['lab_name'], unique=True)
    op.create_index('idx_kb_lab_thresholds_status', 'kb_lab_thresholds', ['status'], unique=False)
    op.create_index(op.f('ix_kb_lab_thresholds_id'), 'kb_lab_thresholds', ['id'], unique=False)
    
    # Create kb_medical_modifier_rules table
    op.create_table(
        'kb_medical_modifier_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('modifier_id', sa.String(length=100), nullable=False),
        sa.Column('condition_id', sa.String(length=100), nullable=False),
        sa.Column('category_id', sa.String(length=100), nullable=True),
        sa.Column('modification_type', sa.String(length=50), nullable=False),
        sa.Column('modification_value', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('applies_to_meals', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('applies_to_exchange_categories', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(length=200), nullable=True),
        sa.Column('source_reference', sa.String(length=500), nullable=True),
        sa.Column('version', sa.String(length=20), nullable=True, server_default='1.0'),
        sa.Column('status', sa.String(length=20), nullable=True, server_default='active'),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column('reviewed_by', sa.String(length=100), nullable=True),
        sa.Column('review_date', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('modifier_id')
    )
    op.create_index('idx_kb_medical_modifier_rules_modifier_id', 'kb_medical_modifier_rules', ['modifier_id'], unique=True)
    op.create_index('idx_kb_medical_modifier_rules_condition_id', 'kb_medical_modifier_rules', ['condition_id'], unique=False)
    op.create_index('idx_kb_medical_modifier_rules_priority', 'kb_medical_modifier_rules', ['priority'], unique=False)
    op.create_index('idx_kb_medical_modifier_rules_status', 'kb_medical_modifier_rules', ['status'], unique=False)
    op.create_index(op.f('ix_kb_medical_modifier_rules_id'), 'kb_medical_modifier_rules', ['id'], unique=False)
    
    # Create kb_food_condition_compatibility table
    op.create_table(
        'kb_food_condition_compatibility',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('food_id', sa.String(length=100), nullable=False),
        sa.Column('condition_id', sa.String(length=100), nullable=False),
        sa.Column('compatibility', sa.String(length=50), nullable=False),
        sa.Column('severity_modifier', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('portion_limit', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('preparation_notes', sa.String(length=500), nullable=True),
        sa.Column('evidence', sa.String(length=500), nullable=True),
        sa.Column('source', sa.String(length=200), nullable=True),
        sa.Column('source_reference', sa.String(length=500), nullable=True),
        sa.Column('version', sa.String(length=20), nullable=True, server_default='1.0'),
        sa.Column('status', sa.String(length=20), nullable=True, server_default='active'),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column('reviewed_by', sa.String(length=100), nullable=True),
        sa.Column('review_date', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('food_id', 'condition_id', name='idx_kb_food_condition_compatibility_food_condition')
    )
    op.create_index('idx_kb_food_condition_compatibility_food_id', 'kb_food_condition_compatibility', ['food_id'], unique=False)
    op.create_index('idx_kb_food_condition_compatibility_condition_id', 'kb_food_condition_compatibility', ['condition_id'], unique=False)
    op.create_index('idx_kb_food_condition_compatibility_compatibility', 'kb_food_condition_compatibility', ['compatibility'], unique=False)
    op.create_index('idx_kb_food_condition_compatibility_status', 'kb_food_condition_compatibility', ['status'], unique=False)
    op.create_index(op.f('ix_kb_food_condition_compatibility_id'), 'kb_food_condition_compatibility', ['id'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_kb_food_condition_compatibility_id'), table_name='kb_food_condition_compatibility')
    op.drop_index('idx_kb_food_condition_compatibility_status', table_name='kb_food_condition_compatibility')
    op.drop_index('idx_kb_food_condition_compatibility_compatibility', table_name='kb_food_condition_compatibility')
    op.drop_index('idx_kb_food_condition_compatibility_condition_id', table_name='kb_food_condition_compatibility')
    op.drop_index('idx_kb_food_condition_compatibility_food_id', table_name='kb_food_condition_compatibility')
    
    op.drop_index(op.f('ix_kb_medical_modifier_rules_id'), table_name='kb_medical_modifier_rules')
    op.drop_index('idx_kb_medical_modifier_rules_status', table_name='kb_medical_modifier_rules')
    op.drop_index('idx_kb_medical_modifier_rules_priority', table_name='kb_medical_modifier_rules')
    op.drop_index('idx_kb_medical_modifier_rules_condition_id', table_name='kb_medical_modifier_rules')
    op.drop_index('idx_kb_medical_modifier_rules_modifier_id', table_name='kb_medical_modifier_rules')
    
    op.drop_index(op.f('ix_kb_lab_thresholds_id'), table_name='kb_lab_thresholds')
    op.drop_index('idx_kb_lab_thresholds_status', table_name='kb_lab_thresholds')
    op.drop_index('idx_kb_lab_thresholds_lab_name', table_name='kb_lab_thresholds')
    
    # Drop tables
    op.drop_table('kb_food_condition_compatibility')
    op.drop_table('kb_medical_modifier_rules')
    op.drop_table('kb_lab_thresholds')

