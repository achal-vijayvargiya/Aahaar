"""Add KB fields and new KB tables

Revision ID: platform_002
Revises: platform_001
Create Date: 2025-12-20 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'platform_002'
down_revision = 'platform_001'
branch_labels = None
depends_on = None


def upgrade():
    """Add new fields to existing KB tables and create new KB tables"""
    
    # 1. Enhance kb_medical_conditions table
    op.add_column('kb_medical_conditions', 
        sa.Column('condition_id', sa.String(100), nullable=True))
    op.add_column('kb_medical_conditions', 
        sa.Column('display_name', sa.String(200), nullable=True))
    op.add_column('kb_medical_conditions', 
        sa.Column('category', sa.String(50), nullable=True))
    op.add_column('kb_medical_conditions', 
        sa.Column('description', sa.String(1000), nullable=True))
    op.add_column('kb_medical_conditions', 
        sa.Column('critical_labs', postgresql.JSONB(), nullable=True))
    op.add_column('kb_medical_conditions', 
        sa.Column('severity_thresholds', postgresql.JSONB(), nullable=True))
    op.add_column('kb_medical_conditions', 
        sa.Column('associated_risks', postgresql.JSONB(), nullable=True))
    op.add_column('kb_medical_conditions', 
        sa.Column('nutrition_focus_areas', postgresql.JSONB(), nullable=True))
    op.add_column('kb_medical_conditions', 
        sa.Column('red_flags', postgresql.JSONB(), nullable=True))
    op.add_column('kb_medical_conditions', 
        sa.Column('source_reference', sa.String(500), nullable=True))
    op.add_column('kb_medical_conditions', 
        sa.Column('status', sa.String(20), nullable=True, server_default=sa.text("'active'")))
    op.add_column('kb_medical_conditions', 
        sa.Column('updated_at', sa.DateTime(), nullable=True))
    op.add_column('kb_medical_conditions', 
        sa.Column('reviewed_by', sa.String(100), nullable=True))
    op.add_column('kb_medical_conditions', 
        sa.Column('review_date', sa.DateTime(), nullable=True))
    
    # Update version default
    op.alter_column('kb_medical_conditions', 'version',
                    existing_type=sa.String(),
                    server_default=sa.text("'1.0'"),
                    nullable=True)
    
    # Create indexes for kb_medical_conditions
    op.create_index('idx_condition_id', 'kb_medical_conditions', ['condition_id'], unique=True)
    op.create_index('idx_category', 'kb_medical_conditions', ['category'], unique=False)
    op.create_index('idx_status', 'kb_medical_conditions', ['status'], unique=False)
    
    # 2. Enhance kb_nutrition_diagnoses table
    op.add_column('kb_nutrition_diagnoses', 
        sa.Column('diagnosis_id', sa.String(100), nullable=True))
    op.add_column('kb_nutrition_diagnoses', 
        sa.Column('problem_statement', sa.String(500), nullable=True))
    op.add_column('kb_nutrition_diagnoses', 
        sa.Column('trigger_conditions', postgresql.JSONB(), nullable=True))
    op.add_column('kb_nutrition_diagnoses', 
        sa.Column('trigger_labs', postgresql.JSONB(), nullable=True))
    op.add_column('kb_nutrition_diagnoses', 
        sa.Column('trigger_anthropometry', postgresql.JSONB(), nullable=True))
    op.add_column('kb_nutrition_diagnoses', 
        sa.Column('trigger_diet_history', postgresql.JSONB(), nullable=True))
    op.add_column('kb_nutrition_diagnoses', 
        sa.Column('severity_logic', sa.String(100), nullable=True))
    op.add_column('kb_nutrition_diagnoses', 
        sa.Column('evidence_types', postgresql.JSONB(), nullable=True))
    op.add_column('kb_nutrition_diagnoses', 
        sa.Column('affected_domains', postgresql.JSONB(), nullable=True))
    op.add_column('kb_nutrition_diagnoses', 
        sa.Column('linked_conditions', postgresql.JSONB(), nullable=True))
    op.add_column('kb_nutrition_diagnoses', 
        sa.Column('source_reference', sa.String(500), nullable=True))
    op.add_column('kb_nutrition_diagnoses', 
        sa.Column('status', sa.String(20), nullable=True, server_default=sa.text("'active'")))
    op.add_column('kb_nutrition_diagnoses', 
        sa.Column('updated_at', sa.DateTime(), nullable=True))
    op.add_column('kb_nutrition_diagnoses', 
        sa.Column('reviewed_by', sa.String(100), nullable=True))
    op.add_column('kb_nutrition_diagnoses', 
        sa.Column('review_date', sa.DateTime(), nullable=True))
    
    # Update version default
    op.alter_column('kb_nutrition_diagnoses', 'version',
                    existing_type=sa.String(),
                    server_default=sa.text("'1.0'"),
                    nullable=True)
    
    # Create indexes for kb_nutrition_diagnoses
    op.create_index('idx_diagnosis_id', 'kb_nutrition_diagnoses', ['diagnosis_id'], unique=True)
    op.create_index('idx_status', 'kb_nutrition_diagnoses', ['status'], unique=False)
    
    # 3. Enhance kb_mnt_rules table
    op.add_column('kb_mnt_rules', 
        sa.Column('rule_id', sa.String(100), nullable=True))
    op.add_column('kb_mnt_rules', 
        sa.Column('applies_to_diagnoses', postgresql.JSONB(), nullable=True))
    op.add_column('kb_mnt_rules', 
        sa.Column('priority_level', sa.Integer(), nullable=True))
    op.add_column('kb_mnt_rules', 
        sa.Column('priority_label', sa.String(20), nullable=True))
    op.add_column('kb_mnt_rules', 
        sa.Column('macro_constraints', postgresql.JSONB(), nullable=True))
    op.add_column('kb_mnt_rules', 
        sa.Column('micro_constraints', postgresql.JSONB(), nullable=True))
    op.add_column('kb_mnt_rules', 
        sa.Column('food_exclusions', postgresql.JSONB(), nullable=True))
    op.add_column('kb_mnt_rules', 
        sa.Column('food_inclusions', postgresql.JSONB(), nullable=True))
    op.add_column('kb_mnt_rules', 
        sa.Column('meal_distribution', postgresql.JSONB(), nullable=True))
    op.add_column('kb_mnt_rules', 
        sa.Column('override_allowed', sa.Boolean(), nullable=True, server_default=sa.text('false')))
    op.add_column('kb_mnt_rules', 
        sa.Column('conflict_resolution', sa.String(200), nullable=True))
    op.add_column('kb_mnt_rules', 
        sa.Column('evidence_level', sa.String(10), nullable=True))
    op.add_column('kb_mnt_rules', 
        sa.Column('source_reference', sa.String(500), nullable=True))
    op.add_column('kb_mnt_rules', 
        sa.Column('status', sa.String(20), nullable=True, server_default=sa.text("'active'")))
    op.add_column('kb_mnt_rules', 
        sa.Column('updated_at', sa.DateTime(), nullable=True))
    op.add_column('kb_mnt_rules', 
        sa.Column('reviewed_by', sa.String(100), nullable=True))
    op.add_column('kb_mnt_rules', 
        sa.Column('review_date', sa.DateTime(), nullable=True))
    
    # Update version default
    op.alter_column('kb_mnt_rules', 'version',
                    existing_type=sa.String(),
                    server_default=sa.text("'1.0'"),
                    nullable=True)
    
    # Create indexes for kb_mnt_rules
    op.create_index('idx_rule_id', 'kb_mnt_rules', ['rule_id'], unique=True)
    op.create_index('idx_priority_level', 'kb_mnt_rules', ['priority_level'], unique=False)
    op.create_index('idx_status', 'kb_mnt_rules', ['status'], unique=False)
    
    # 4. Create kb_lab_thresholds table
    op.create_table(
        'kb_lab_thresholds',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('lab_name', sa.String(100), nullable=False),
        sa.Column('display_name', sa.String(200), nullable=False),
        sa.Column('normal_range', postgresql.JSONB(), nullable=True),
        sa.Column('abnormal_ranges', postgresql.JSONB(), nullable=True),
        sa.Column('units', postgresql.JSONB(), nullable=True),
        sa.Column('conversion_factors', postgresql.JSONB(), nullable=True),
        sa.Column('source', sa.String(200), nullable=True),
        sa.Column('source_reference', sa.String(500), nullable=True),
        sa.Column('version', sa.String(20), nullable=True, server_default=sa.text("'1.0'")),
        sa.Column('status', sa.String(20), nullable=True, server_default=sa.text("'active'")),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('last_updated', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_kb_lab_thresholds_id', 'kb_lab_thresholds', ['id'], unique=False)
    op.create_index('idx_lab_name', 'kb_lab_thresholds', ['lab_name'], unique=True)
    op.create_index('idx_status', 'kb_lab_thresholds', ['status'], unique=False)
    
    # 5. Create kb_medical_modifier_rules table
    op.create_table(
        'kb_medical_modifier_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('modifier_id', sa.String(100), nullable=False),
        sa.Column('condition_id', sa.String(100), nullable=False),
        sa.Column('category_id', sa.String(100), nullable=True),
        sa.Column('modification_type', sa.String(50), nullable=False),
        sa.Column('modification_value', postgresql.JSONB(), nullable=False),
        sa.Column('applies_to_meals', postgresql.JSONB(), nullable=True),
        sa.Column('applies_to_exchange_categories', postgresql.JSONB(), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(200), nullable=True),
        sa.Column('source_reference', sa.String(500), nullable=True),
        sa.Column('version', sa.String(20), nullable=True, server_default=sa.text("'1.0'")),
        sa.Column('status', sa.String(20), nullable=True, server_default=sa.text("'active'")),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('reviewed_by', sa.String(100), nullable=True),
        sa.Column('review_date', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_kb_medical_modifier_rules_id', 'kb_medical_modifier_rules', ['id'], unique=False)
    op.create_index('idx_modifier_id', 'kb_medical_modifier_rules', ['modifier_id'], unique=True)
    op.create_index('idx_condition_id', 'kb_medical_modifier_rules', ['condition_id'], unique=False)
    op.create_index('idx_priority', 'kb_medical_modifier_rules', ['priority'], unique=False)
    op.create_index('idx_status', 'kb_medical_modifier_rules', ['status'], unique=False)
    
    # 6. Create kb_food_condition_compatibility table
    op.create_table(
        'kb_food_condition_compatibility',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('food_id', sa.String(100), nullable=False),
        sa.Column('condition_id', sa.String(100), nullable=False),
        sa.Column('compatibility', sa.String(50), nullable=False),
        sa.Column('severity_modifier', postgresql.JSONB(), nullable=True),
        sa.Column('portion_limit', postgresql.JSONB(), nullable=True),
        sa.Column('preparation_notes', sa.String(500), nullable=True),
        sa.Column('evidence', sa.String(500), nullable=True),
        sa.Column('source', sa.String(200), nullable=True),
        sa.Column('source_reference', sa.String(500), nullable=True),
        sa.Column('version', sa.String(20), nullable=True, server_default=sa.text("'1.0'")),
        sa.Column('status', sa.String(20), nullable=True, server_default=sa.text("'active'")),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('reviewed_by', sa.String(100), nullable=True),
        sa.Column('review_date', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_kb_food_condition_compatibility_id', 'kb_food_condition_compatibility', ['id'], unique=False)
    op.create_index('idx_food_condition', 'kb_food_condition_compatibility', ['food_id', 'condition_id'], unique=True)
    op.create_index('idx_food_id', 'kb_food_condition_compatibility', ['food_id'], unique=False)
    op.create_index('idx_condition_id', 'kb_food_condition_compatibility', ['condition_id'], unique=False)
    op.create_index('idx_compatibility', 'kb_food_condition_compatibility', ['compatibility'], unique=False)
    op.create_index('idx_status', 'kb_food_condition_compatibility', ['status'], unique=False)


def downgrade():
    """Remove new KB fields and drop new KB tables"""
    
    # Drop new KB tables first
    op.drop_index('idx_status', table_name='kb_food_condition_compatibility')
    op.drop_index('idx_compatibility', table_name='kb_food_condition_compatibility')
    op.drop_index('idx_condition_id', table_name='kb_food_condition_compatibility')
    op.drop_index('idx_food_id', table_name='kb_food_condition_compatibility')
    op.drop_index('idx_food_condition', table_name='kb_food_condition_compatibility')
    op.drop_index('ix_kb_food_condition_compatibility_id', table_name='kb_food_condition_compatibility')
    op.drop_table('kb_food_condition_compatibility')
    
    op.drop_index('idx_status', table_name='kb_medical_modifier_rules')
    op.drop_index('idx_priority', table_name='kb_medical_modifier_rules')
    op.drop_index('idx_condition_id', table_name='kb_medical_modifier_rules')
    op.drop_index('idx_modifier_id', table_name='kb_medical_modifier_rules')
    op.drop_index('ix_kb_medical_modifier_rules_id', table_name='kb_medical_modifier_rules')
    op.drop_table('kb_medical_modifier_rules')
    
    op.drop_index('idx_status', table_name='kb_lab_thresholds')
    op.drop_index('idx_lab_name', table_name='kb_lab_thresholds')
    op.drop_index('ix_kb_lab_thresholds_id', table_name='kb_lab_thresholds')
    op.drop_table('kb_lab_thresholds')
    
    # Remove indexes from enhanced tables
    op.drop_index('idx_status', table_name='kb_mnt_rules')
    op.drop_index('idx_priority_level', table_name='kb_mnt_rules')
    op.drop_index('idx_rule_id', table_name='kb_mnt_rules')
    
    op.drop_index('idx_status', table_name='kb_nutrition_diagnoses')
    op.drop_index('idx_diagnosis_id', table_name='kb_nutrition_diagnoses')
    
    op.drop_index('idx_status', table_name='kb_medical_conditions')
    op.drop_index('idx_category', table_name='kb_medical_conditions')
    op.drop_index('idx_condition_id', table_name='kb_medical_conditions')
    
    # Remove columns from kb_mnt_rules
    op.drop_column('kb_mnt_rules', 'review_date')
    op.drop_column('kb_mnt_rules', 'reviewed_by')
    op.drop_column('kb_mnt_rules', 'updated_at')
    op.drop_column('kb_mnt_rules', 'status')
    op.drop_column('kb_mnt_rules', 'source_reference')
    op.drop_column('kb_mnt_rules', 'evidence_level')
    op.drop_column('kb_mnt_rules', 'conflict_resolution')
    op.drop_column('kb_mnt_rules', 'override_allowed')
    op.drop_column('kb_mnt_rules', 'meal_distribution')
    op.drop_column('kb_mnt_rules', 'food_inclusions')
    op.drop_column('kb_mnt_rules', 'food_exclusions')
    op.drop_column('kb_mnt_rules', 'micro_constraints')
    op.drop_column('kb_mnt_rules', 'macro_constraints')
    op.drop_column('kb_mnt_rules', 'priority_label')
    op.drop_column('kb_mnt_rules', 'priority_level')
    op.drop_column('kb_mnt_rules', 'applies_to_diagnoses')
    op.drop_column('kb_mnt_rules', 'rule_id')
    
    # Remove columns from kb_nutrition_diagnoses
    op.drop_column('kb_nutrition_diagnoses', 'review_date')
    op.drop_column('kb_nutrition_diagnoses', 'reviewed_by')
    op.drop_column('kb_nutrition_diagnoses', 'updated_at')
    op.drop_column('kb_nutrition_diagnoses', 'status')
    op.drop_column('kb_nutrition_diagnoses', 'source_reference')
    op.drop_column('kb_nutrition_diagnoses', 'linked_conditions')
    op.drop_column('kb_nutrition_diagnoses', 'affected_domains')
    op.drop_column('kb_nutrition_diagnoses', 'evidence_types')
    op.drop_column('kb_nutrition_diagnoses', 'severity_logic')
    op.drop_column('kb_nutrition_diagnoses', 'trigger_diet_history')
    op.drop_column('kb_nutrition_diagnoses', 'trigger_anthropometry')
    op.drop_column('kb_nutrition_diagnoses', 'trigger_labs')
    op.drop_column('kb_nutrition_diagnoses', 'trigger_conditions')
    op.drop_column('kb_nutrition_diagnoses', 'problem_statement')
    op.drop_column('kb_nutrition_diagnoses', 'diagnosis_id')
    
    # Remove columns from kb_medical_conditions
    op.drop_column('kb_medical_conditions', 'review_date')
    op.drop_column('kb_medical_conditions', 'reviewed_by')
    op.drop_column('kb_medical_conditions', 'updated_at')
    op.drop_column('kb_medical_conditions', 'status')
    op.drop_column('kb_medical_conditions', 'source_reference')
    op.drop_column('kb_medical_conditions', 'red_flags')
    op.drop_column('kb_medical_conditions', 'nutrition_focus_areas')
    op.drop_column('kb_medical_conditions', 'associated_risks')
    op.drop_column('kb_medical_conditions', 'severity_thresholds')
    op.drop_column('kb_medical_conditions', 'critical_labs')
    op.drop_column('kb_medical_conditions', 'description')
    op.drop_column('kb_medical_conditions', 'category')
    op.drop_column('kb_medical_conditions', 'display_name')
    op.drop_column('kb_medical_conditions', 'condition_id')
    
    # Reset version defaults
    op.alter_column('kb_mnt_rules', 'version',
                    existing_type=sa.String(),
                    server_default=None,
                    nullable=True)
    op.alter_column('kb_nutrition_diagnoses', 'version',
                    existing_type=sa.String(),
                    server_default=None,
                    nullable=True)
    op.alter_column('kb_medical_conditions', 'version',
                    existing_type=sa.String(),
                    server_default=None,
                    nullable=True)

