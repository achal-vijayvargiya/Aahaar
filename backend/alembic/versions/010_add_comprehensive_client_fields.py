"""add comprehensive client and health profile fields

Revision ID: 010_comprehensive_fields
Revises: 009_enhanced_health_profile
Create Date: 2025-01-16 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '010_comprehensive_fields'
down_revision = '009_enhanced_health_profile'
branch_labels = None
depends_on = None


def upgrade():
    # Add new fields to clients table
    op.add_column('clients', sa.Column('city', sa.String(), nullable=True))
    op.add_column('clients', sa.Column('emergency_contact_name', sa.String(), nullable=True))
    op.add_column('clients', sa.Column('emergency_contact_phone', sa.String(), nullable=True))
    op.add_column('clients', sa.Column('emergency_contact_relation', sa.String(), nullable=True))
    
    # Add new fields to health_profiles table
    op.add_column('health_profiles', sa.Column('waist_circumference', sa.Float(), nullable=True))
    op.add_column('health_profiles', sa.Column('surgery_history', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'))
    op.add_column('health_profiles', sa.Column('blood_report', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'))
    op.add_column('health_profiles', sa.Column('menstruation_cycle', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'))
    op.add_column('health_profiles', sa.Column('goals_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'))
    op.add_column('health_profiles', sa.Column('food_preferences', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'))


def downgrade():
    # Remove new fields from health_profiles table
    op.drop_column('health_profiles', 'food_preferences')
    op.drop_column('health_profiles', 'goals_json')
    op.drop_column('health_profiles', 'menstruation_cycle')
    op.drop_column('health_profiles', 'blood_report')
    op.drop_column('health_profiles', 'surgery_history')
    op.drop_column('health_profiles', 'waist_circumference')
    
    # Remove new fields from clients table
    op.drop_column('clients', 'emergency_contact_relation')
    op.drop_column('clients', 'emergency_contact_phone')
    op.drop_column('clients', 'emergency_contact_name')
    op.drop_column('clients', 'city')

