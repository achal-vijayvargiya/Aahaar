"""add comprehensive health profile fields

Revision ID: 009_enhanced_health_profile
Revises: 008_add_enriched_food_models
Create Date: 2025-01-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '009_enhanced_health_profile'
down_revision = '008_add_enriched_food_models'
branch_labels = None
depends_on = None


def upgrade():
    # Add comprehensive health profile fields to existing health_profiles table
    
    # Basic Profile - Additional fields
    op.add_column('health_profiles', sa.Column('gender', sa.String(length=20), nullable=True))
    op.add_column('health_profiles', sa.Column('target_weight_kg', sa.Float(), nullable=True))
    
    # Goals - Structured
    op.add_column('health_profiles', sa.Column('primary_goal', sa.String(length=100), nullable=True))
    op.add_column('health_profiles', sa.Column('secondary_goals', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'))
    
    # Medical Conditions - Structured JSON
    op.add_column('health_profiles', sa.Column('medical_conditions_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'))
    
    # Allergies - Array format (complements existing text field)
    op.add_column('health_profiles', sa.Column('allergies_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'))
    
    # Medications - Structured JSON (complements existing text field)
    op.add_column('health_profiles', sa.Column('medications_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'))
    
    # Supplements - Array format (complements existing text field)
    op.add_column('health_profiles', sa.Column('supplements_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'))
    
    # Ayurveda - Structured JSON
    op.add_column('health_profiles', sa.Column('ayurveda_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'))
    
    # Gut Health - Structured JSON
    op.add_column('health_profiles', sa.Column('gut_health_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'))
    
    # Dietary Preferences - Array format
    op.add_column('health_profiles', sa.Column('dietary_preferences', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'))
    
    # Lifestyle - Structured JSON
    op.add_column('health_profiles', sa.Column('lifestyle_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'))


def downgrade():
    # Remove comprehensive health profile fields
    op.drop_column('health_profiles', 'lifestyle_data')
    op.drop_column('health_profiles', 'dietary_preferences')
    op.drop_column('health_profiles', 'gut_health_data')
    op.drop_column('health_profiles', 'ayurveda_data')
    op.drop_column('health_profiles', 'supplements_json')
    op.drop_column('health_profiles', 'medications_json')
    op.drop_column('health_profiles', 'allergies_json')
    op.drop_column('health_profiles', 'medical_conditions_json')
    op.drop_column('health_profiles', 'secondary_goals')
    op.drop_column('health_profiles', 'primary_goal')
    op.drop_column('health_profiles', 'target_weight_kg')
    op.drop_column('health_profiles', 'gender')

