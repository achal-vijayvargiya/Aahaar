"""platform_001

Revision ID: platform_001
Revises: 010_comprehensive_fields
Create Date: 2025-12-14 18:27:34.609274

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'platform_001'
down_revision: Union[str, None] = '010_comprehensive_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create Knowledge Base tables
    op.create_table('kb_ayurveda_profiles',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('version', sa.String(), nullable=True),
    sa.Column('source', sa.String(), nullable=True),
    sa.Column('last_reviewed', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_kb_ayurveda_profiles_id'), 'kb_ayurveda_profiles', ['id'], unique=False)
    
    op.create_table('kb_foods',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('version', sa.String(), nullable=True),
    sa.Column('source', sa.String(), nullable=True),
    sa.Column('last_reviewed', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_kb_foods_id'), 'kb_foods', ['id'], unique=False)
    
    op.create_table('kb_medical_conditions',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('version', sa.String(), nullable=True),
    sa.Column('source', sa.String(), nullable=True),
    sa.Column('last_reviewed', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_kb_medical_conditions_id'), 'kb_medical_conditions', ['id'], unique=False)
    
    op.create_table('kb_mnt_rules',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('version', sa.String(), nullable=True),
    sa.Column('source', sa.String(), nullable=True),
    sa.Column('last_reviewed', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_kb_mnt_rules_id'), 'kb_mnt_rules', ['id'], unique=False)
    
    op.create_table('kb_nutrition_diagnoses',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('version', sa.String(), nullable=True),
    sa.Column('source', sa.String(), nullable=True),
    sa.Column('last_reviewed', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_kb_nutrition_diagnoses_id'), 'kb_nutrition_diagnoses', ['id'], unique=False)
    
    # Create Platform Client table (base table)
    op.create_table('platform_clients',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('external_client_id', sa.String(), nullable=True),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('age', sa.Integer(), nullable=True),
    sa.Column('gender', sa.String(), nullable=True),
    sa.Column('height_cm', sa.Float(), nullable=True),
    sa.Column('weight_kg', sa.Float(), nullable=True),
    sa.Column('location', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_platform_clients_id'), 'platform_clients', ['id'], unique=False)
    
    # Create Platform Decision Logs table
    op.create_table('platform_decision_logs',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('entity_type', sa.String(), nullable=True),
    sa.Column('entity_id', sa.UUID(), nullable=True),
    sa.Column('rule_ids_used', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_platform_decision_logs_id'), 'platform_decision_logs', ['id'], unique=False)
    
    # Create Platform Intake table (depends on platform_clients)
    op.create_table('platform_intakes',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('client_id', sa.UUID(), nullable=False),
    sa.Column('raw_input', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('normalized_input', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('source', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['client_id'], ['platform_clients.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_platform_intakes_id'), 'platform_intakes', ['id'], unique=False)
    
    # Create Platform Assessment table (depends on platform_clients and platform_intakes)
    op.create_table('platform_assessments',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('client_id', sa.UUID(), nullable=False),
    sa.Column('intake_id', sa.UUID(), nullable=True),
    sa.Column('assessment_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('assessment_status', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['client_id'], ['platform_clients.id'], ),
    sa.ForeignKeyConstraint(['intake_id'], ['platform_intakes.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_platform_assessments_id'), 'platform_assessments', ['id'], unique=False)
    
    # Create Platform Ayurveda Profile table (depends on platform_assessments)
    op.create_table('platform_ayurveda_profiles',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('assessment_id', sa.UUID(), nullable=False),
    sa.Column('dosha_primary', sa.String(), nullable=True),
    sa.Column('dosha_secondary', sa.String(), nullable=True),
    sa.Column('vikriti_notes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('lifestyle_guidelines', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['assessment_id'], ['platform_assessments.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_platform_ayurveda_profiles_id'), 'platform_ayurveda_profiles', ['id'], unique=False)
    
    # Create Platform Diagnosis table (depends on platform_assessments)
    op.create_table('platform_diagnoses',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('assessment_id', sa.UUID(), nullable=False),
    sa.Column('diagnosis_type', sa.String(), nullable=True),
    sa.Column('diagnosis_id', sa.String(), nullable=True),
    sa.Column('severity_score', sa.Numeric(), nullable=True),
    sa.Column('evidence', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['assessment_id'], ['platform_assessments.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_platform_diagnoses_id'), 'platform_diagnoses', ['id'], unique=False)
    
    # Create Platform MNT Constraint table (depends on platform_assessments)
    op.create_table('platform_mnt_constraints',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('assessment_id', sa.UUID(), nullable=False),
    sa.Column('rule_id', sa.String(), nullable=True),
    sa.Column('priority', sa.Integer(), nullable=True),
    sa.Column('macro_constraints', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('micro_constraints', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('food_exclusions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['assessment_id'], ['platform_assessments.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_platform_mnt_constraints_id'), 'platform_mnt_constraints', ['id'], unique=False)
    
    # Create Platform Nutrition Target table (depends on platform_assessments)
    op.create_table('platform_nutrition_targets',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('assessment_id', sa.UUID(), nullable=False),
    sa.Column('calories_target', sa.Numeric(), nullable=True),
    sa.Column('macros', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('key_micros', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('calculation_source', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['assessment_id'], ['platform_assessments.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_platform_nutrition_targets_id'), 'platform_nutrition_targets', ['id'], unique=False)
    
    # Create Platform Diet Plan table (depends on platform_clients and platform_assessments)
    op.create_table('platform_diet_plans',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('client_id', sa.UUID(), nullable=False),
    sa.Column('assessment_id', sa.UUID(), nullable=False),
    sa.Column('plan_version', sa.Integer(), nullable=True),
    sa.Column('status', sa.String(), nullable=True),
    sa.Column('meal_plan', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('explanations', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('constraints_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['assessment_id'], ['platform_assessments.id'], ),
    sa.ForeignKeyConstraint(['client_id'], ['platform_clients.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_platform_diet_plans_id'), 'platform_diet_plans', ['id'], unique=False)
    
    # Create Platform Monitoring Record table (depends on platform_clients and platform_diet_plans)
    op.create_table('platform_monitoring_records',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('client_id', sa.UUID(), nullable=False),
    sa.Column('plan_id', sa.UUID(), nullable=True),
    sa.Column('metric_type', sa.String(), nullable=True),
    sa.Column('metric_value', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('recorded_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['client_id'], ['platform_clients.id'], ),
    sa.ForeignKeyConstraint(['plan_id'], ['platform_diet_plans.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_platform_monitoring_records_id'), 'platform_monitoring_records', ['id'], unique=False)


def downgrade() -> None:
    # Drop Platform tables in reverse order of dependencies
    op.drop_index(op.f('ix_platform_monitoring_records_id'), table_name='platform_monitoring_records')
    op.drop_table('platform_monitoring_records')
    
    op.drop_index(op.f('ix_platform_diet_plans_id'), table_name='platform_diet_plans')
    op.drop_table('platform_diet_plans')
    
    op.drop_index(op.f('ix_platform_nutrition_targets_id'), table_name='platform_nutrition_targets')
    op.drop_table('platform_nutrition_targets')
    
    op.drop_index(op.f('ix_platform_mnt_constraints_id'), table_name='platform_mnt_constraints')
    op.drop_table('platform_mnt_constraints')
    
    op.drop_index(op.f('ix_platform_diagnoses_id'), table_name='platform_diagnoses')
    op.drop_table('platform_diagnoses')
    
    op.drop_index(op.f('ix_platform_ayurveda_profiles_id'), table_name='platform_ayurveda_profiles')
    op.drop_table('platform_ayurveda_profiles')
    
    op.drop_index(op.f('ix_platform_assessments_id'), table_name='platform_assessments')
    op.drop_table('platform_assessments')
    
    op.drop_index(op.f('ix_platform_intakes_id'), table_name='platform_intakes')
    op.drop_table('platform_intakes')
    
    op.drop_index(op.f('ix_platform_decision_logs_id'), table_name='platform_decision_logs')
    op.drop_table('platform_decision_logs')
    
    op.drop_index(op.f('ix_platform_clients_id'), table_name='platform_clients')
    op.drop_table('platform_clients')
    
    # Drop Knowledge Base tables
    op.drop_index(op.f('ix_kb_nutrition_diagnoses_id'), table_name='kb_nutrition_diagnoses')
    op.drop_table('kb_nutrition_diagnoses')
    
    op.drop_index(op.f('ix_kb_mnt_rules_id'), table_name='kb_mnt_rules')
    op.drop_table('kb_mnt_rules')
    
    op.drop_index(op.f('ix_kb_medical_conditions_id'), table_name='kb_medical_conditions')
    op.drop_table('kb_medical_conditions')
    
    op.drop_index(op.f('ix_kb_foods_id'), table_name='kb_foods')
    op.drop_table('kb_foods')
    
    op.drop_index(op.f('ix_kb_ayurveda_profiles_id'), table_name='kb_ayurveda_profiles')
    op.drop_table('kb_ayurveda_profiles')
