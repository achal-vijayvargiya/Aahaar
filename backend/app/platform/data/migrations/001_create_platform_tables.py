"""Create platform tables

Revision ID: platform_001
Revises: 
Create Date: 2025-12-13 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'platform_001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Create all platform tables"""
    
    # 1. platform_users
    op.create_table(
        'platform_users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('role', sa.String(), nullable=True, server_default=sa.text("'doctor'")),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default=sa.text('true')),
        sa.Column('is_superuser', sa.Boolean(), nullable=True, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_platform_users_id', 'platform_users', ['id'], unique=False)
    op.create_index('ix_platform_users_email', 'platform_users', ['email'], unique=True)
    op.create_index('ix_platform_users_username', 'platform_users', ['username'], unique=True)
    
    # 2. platform_clients
    op.create_table(
        'platform_clients',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
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
    op.create_index('ix_platform_clients_id', 'platform_clients', ['id'], unique=False)
    op.create_index('ix_platform_clients_external_client_id', 'platform_clients', ['external_client_id'], unique=False)
    
    # 3. platform_intakes
    op.create_table(
        'platform_intakes',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('raw_input', postgresql.JSONB(), nullable=True),
        sa.Column('normalized_input', postgresql.JSONB(), nullable=True),
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['platform_clients.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_platform_intakes_id', 'platform_intakes', ['id'], unique=False)
    op.create_index('ix_platform_intakes_client_id', 'platform_intakes', ['client_id'], unique=False)
    
    # 4. platform_assessments
    op.create_table(
        'platform_assessments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('intake_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('assessment_snapshot', postgresql.JSONB(), nullable=True),
        sa.Column('assessment_status', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['platform_clients.id'], ),
        sa.ForeignKeyConstraint(['intake_id'], ['platform_intakes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_platform_assessments_id', 'platform_assessments', ['id'], unique=False)
    op.create_index('ix_platform_assessments_client_id', 'platform_assessments', ['client_id'], unique=False)
    op.create_index('ix_platform_assessments_intake_id', 'platform_assessments', ['intake_id'], unique=False)
    op.create_index('ix_platform_assessments_status', 'platform_assessments', ['assessment_status'], unique=False)
    
    # 5. platform_diagnoses
    op.create_table(
        'platform_diagnoses',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assessment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('diagnosis_type', sa.String(), nullable=True),
        sa.Column('diagnosis_id', sa.String(), nullable=True),
        sa.Column('severity_score', sa.Numeric(), nullable=True),
        sa.Column('evidence', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['assessment_id'], ['platform_assessments.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_platform_diagnoses_id', 'platform_diagnoses', ['id'], unique=False)
    op.create_index('ix_platform_diagnoses_assessment_id', 'platform_diagnoses', ['assessment_id'], unique=False)
    op.create_index('ix_platform_diagnoses_type', 'platform_diagnoses', ['diagnosis_type'], unique=False)
    op.create_index('ix_platform_diagnoses_diagnosis_id', 'platform_diagnoses', ['diagnosis_id'], unique=False)
    
    # 6. platform_mnt_constraints
    op.create_table(
        'platform_mnt_constraints',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assessment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('rule_id', sa.String(), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=True),
        sa.Column('macro_constraints', postgresql.JSONB(), nullable=True),
        sa.Column('micro_constraints', postgresql.JSONB(), nullable=True),
        sa.Column('food_exclusions', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['assessment_id'], ['platform_assessments.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_platform_mnt_constraints_id', 'platform_mnt_constraints', ['id'], unique=False)
    op.create_index('ix_platform_mnt_constraints_assessment_id', 'platform_mnt_constraints', ['assessment_id'], unique=False)
    op.create_index('ix_platform_mnt_constraints_rule_id', 'platform_mnt_constraints', ['rule_id'], unique=False)
    
    # 7. platform_nutrition_targets
    op.create_table(
        'platform_nutrition_targets',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assessment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('calories_target', sa.Numeric(), nullable=True),
        sa.Column('macros', postgresql.JSONB(), nullable=True),
        sa.Column('key_micros', postgresql.JSONB(), nullable=True),
        sa.Column('calculation_source', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['assessment_id'], ['platform_assessments.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_platform_nutrition_targets_id', 'platform_nutrition_targets', ['id'], unique=False)
    op.create_index('ix_platform_nutrition_targets_assessment_id', 'platform_nutrition_targets', ['assessment_id'], unique=False)
    
    # 8. platform_ayurveda_profiles
    op.create_table(
        'platform_ayurveda_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assessment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('dosha_primary', sa.String(), nullable=True),
        sa.Column('dosha_secondary', sa.String(), nullable=True),
        sa.Column('vikriti_notes', postgresql.JSONB(), nullable=True),
        sa.Column('lifestyle_guidelines', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['assessment_id'], ['platform_assessments.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_platform_ayurveda_profiles_id', 'platform_ayurveda_profiles', ['id'], unique=False)
    op.create_index('ix_platform_ayurveda_profiles_assessment_id', 'platform_ayurveda_profiles', ['assessment_id'], unique=False)
    
    # 8.5. platform_exchange_allocations
    op.create_table(
        'platform_exchange_allocations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assessment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('exchanges_per_meal', postgresql.JSONB(), nullable=False),
        sa.Column('notes', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['assessment_id'], ['platform_assessments.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('assessment_id')
    )
    op.create_index('ix_platform_exchange_allocations_id', 'platform_exchange_allocations', ['id'], unique=False)
    op.create_index('ix_platform_exchange_allocations_assessment_id', 'platform_exchange_allocations', ['assessment_id'], unique=False)
    
    # 9. platform_diet_plans
    op.create_table(
        'platform_diet_plans',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('assessment_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('plan_version', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('meal_plan', postgresql.JSONB(), nullable=True),
        sa.Column('explanations', postgresql.JSONB(), nullable=True),
        sa.Column('constraints_snapshot', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['platform_clients.id'], ),
        sa.ForeignKeyConstraint(['assessment_id'], ['platform_assessments.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_platform_diet_plans_id', 'platform_diet_plans', ['id'], unique=False)
    op.create_index('ix_platform_diet_plans_client_id', 'platform_diet_plans', ['client_id'], unique=False)
    op.create_index('ix_platform_diet_plans_assessment_id', 'platform_diet_plans', ['assessment_id'], unique=False)
    op.create_index('ix_platform_diet_plans_status', 'platform_diet_plans', ['status'], unique=False)
    op.create_index('ix_platform_diet_plans_version', 'platform_diet_plans', ['plan_version'], unique=False)
    
    # 10. platform_monitoring_records
    op.create_table(
        'platform_monitoring_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('metric_type', sa.String(), nullable=True),
        sa.Column('metric_value', postgresql.JSONB(), nullable=True),
        sa.Column('recorded_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['platform_clients.id'], ),
        sa.ForeignKeyConstraint(['plan_id'], ['platform_diet_plans.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_platform_monitoring_records_id', 'platform_monitoring_records', ['id'], unique=False)
    op.create_index('ix_platform_monitoring_records_client_id', 'platform_monitoring_records', ['client_id'], unique=False)
    op.create_index('ix_platform_monitoring_records_plan_id', 'platform_monitoring_records', ['plan_id'], unique=False)
    op.create_index('ix_platform_monitoring_records_metric_type', 'platform_monitoring_records', ['metric_type'], unique=False)
    
    # 11. platform_decision_logs
    op.create_table(
        'platform_decision_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('entity_type', sa.String(), nullable=True),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('rule_ids_used', postgresql.JSONB(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_platform_decision_logs_id', 'platform_decision_logs', ['id'], unique=False)
    op.create_index('ix_platform_decision_logs_entity_type', 'platform_decision_logs', ['entity_type'], unique=False)
    op.create_index('ix_platform_decision_logs_entity_id', 'platform_decision_logs', ['entity_id'], unique=False)
    
    # 12. kb_medical_conditions
    op.create_table(
        'kb_medical_conditions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version', sa.String(), nullable=True),
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('last_reviewed', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_kb_medical_conditions_id', 'kb_medical_conditions', ['id'], unique=False)
    
    # 13. kb_nutrition_diagnoses
    op.create_table(
        'kb_nutrition_diagnoses',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version', sa.String(), nullable=True),
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('last_reviewed', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_kb_nutrition_diagnoses_id', 'kb_nutrition_diagnoses', ['id'], unique=False)
    
    # 14. kb_mnt_rules
    op.create_table(
        'kb_mnt_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version', sa.String(), nullable=True),
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('last_reviewed', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_kb_mnt_rules_id', 'kb_mnt_rules', ['id'], unique=False)
    
    # 15. kb_ayurveda_profiles
    op.create_table(
        'kb_ayurveda_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version', sa.String(), nullable=True),
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('last_reviewed', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_kb_ayurveda_profiles_id', 'kb_ayurveda_profiles', ['id'], unique=False)
    
    # 16. kb_foods
    op.create_table(
        'kb_foods',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version', sa.String(), nullable=True),
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('last_reviewed', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_kb_foods_id', 'kb_foods', ['id'], unique=False)


def downgrade():
    """Drop all platform tables"""
    
    # Drop indexes first, then tables (in reverse order of creation)
    
    # Knowledge base tables
    op.drop_index('ix_kb_foods_id', table_name='kb_foods')
    op.drop_table('kb_foods')
    
    op.drop_index('ix_kb_ayurveda_profiles_id', table_name='kb_ayurveda_profiles')
    op.drop_table('kb_ayurveda_profiles')
    
    op.drop_index('ix_kb_mnt_rules_id', table_name='kb_mnt_rules')
    op.drop_table('kb_mnt_rules')
    
    op.drop_index('ix_kb_nutrition_diagnoses_id', table_name='kb_nutrition_diagnoses')
    op.drop_table('kb_nutrition_diagnoses')
    
    op.drop_index('ix_kb_medical_conditions_id', table_name='kb_medical_conditions')
    op.drop_table('kb_medical_conditions')
    
    # Platform tables
    op.drop_index('ix_platform_decision_logs_entity_id', table_name='platform_decision_logs')
    op.drop_index('ix_platform_decision_logs_entity_type', table_name='platform_decision_logs')
    op.drop_index('ix_platform_decision_logs_id', table_name='platform_decision_logs')
    op.drop_table('platform_decision_logs')
    
    op.drop_index('ix_platform_monitoring_records_metric_type', table_name='platform_monitoring_records')
    op.drop_index('ix_platform_monitoring_records_plan_id', table_name='platform_monitoring_records')
    op.drop_index('ix_platform_monitoring_records_client_id', table_name='platform_monitoring_records')
    op.drop_index('ix_platform_monitoring_records_id', table_name='platform_monitoring_records')
    op.drop_table('platform_monitoring_records')
    
    op.drop_index('ix_platform_diet_plans_version', table_name='platform_diet_plans')
    op.drop_index('ix_platform_diet_plans_status', table_name='platform_diet_plans')
    op.drop_index('ix_platform_diet_plans_assessment_id', table_name='platform_diet_plans')
    op.drop_index('ix_platform_diet_plans_client_id', table_name='platform_diet_plans')
    op.drop_index('ix_platform_diet_plans_id', table_name='platform_diet_plans')
    op.drop_table('platform_diet_plans')
    
    op.drop_index('ix_platform_ayurveda_profiles_assessment_id', table_name='platform_ayurveda_profiles')
    op.drop_index('ix_platform_ayurveda_profiles_id', table_name='platform_ayurveda_profiles')
    op.drop_table('platform_ayurveda_profiles')
    
    op.drop_index('ix_platform_exchange_allocations_assessment_id', table_name='platform_exchange_allocations')
    op.drop_index('ix_platform_exchange_allocations_id', table_name='platform_exchange_allocations')
    op.drop_table('platform_exchange_allocations')
    
    op.drop_index('ix_platform_nutrition_targets_assessment_id', table_name='platform_nutrition_targets')
    op.drop_index('ix_platform_nutrition_targets_id', table_name='platform_nutrition_targets')
    op.drop_table('platform_nutrition_targets')
    
    op.drop_index('ix_platform_mnt_constraints_rule_id', table_name='platform_mnt_constraints')
    op.drop_index('ix_platform_mnt_constraints_assessment_id', table_name='platform_mnt_constraints')
    op.drop_index('ix_platform_mnt_constraints_id', table_name='platform_mnt_constraints')
    op.drop_table('platform_mnt_constraints')
    
    op.drop_index('ix_platform_diagnoses_diagnosis_id', table_name='platform_diagnoses')
    op.drop_index('ix_platform_diagnoses_type', table_name='platform_diagnoses')
    op.drop_index('ix_platform_diagnoses_assessment_id', table_name='platform_diagnoses')
    op.drop_index('ix_platform_diagnoses_id', table_name='platform_diagnoses')
    op.drop_table('platform_diagnoses')
    
    op.drop_index('ix_platform_assessments_status', table_name='platform_assessments')
    op.drop_index('ix_platform_assessments_intake_id', table_name='platform_assessments')
    op.drop_index('ix_platform_assessments_client_id', table_name='platform_assessments')
    op.drop_index('ix_platform_assessments_id', table_name='platform_assessments')
    op.drop_table('platform_assessments')
    
    op.drop_index('ix_platform_intakes_client_id', table_name='platform_intakes')
    op.drop_index('ix_platform_intakes_id', table_name='platform_intakes')
    op.drop_table('platform_intakes')
    
    op.drop_index('ix_platform_clients_external_client_id', table_name='platform_clients')
    op.drop_index('ix_platform_clients_id', table_name='platform_clients')
    op.drop_table('platform_clients')
    
    op.drop_index('ix_platform_users_username', table_name='platform_users')
    op.drop_index('ix_platform_users_email', table_name='platform_users')
    op.drop_index('ix_platform_users_id', table_name='platform_users')
    op.drop_table('platform_users')

