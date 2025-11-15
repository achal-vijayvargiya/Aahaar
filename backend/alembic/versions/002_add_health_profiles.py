"""Add health profiles table

Revision ID: 002
Revises: 001
Create Date: 2025-11-02 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    """Create health_profiles table"""
    
    # Create the health_profiles table
    op.create_table(
        'health_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('age', sa.Integer(), nullable=True),
        sa.Column('weight', sa.Float(), nullable=True),
        sa.Column('height', sa.Float(), nullable=True),
        sa.Column('goals', sa.Text(), nullable=True),
        sa.Column('activity_level', sa.String(length=50), nullable=True),
        sa.Column('disease', sa.Text(), nullable=True),
        sa.Column('allergies', sa.Text(), nullable=True),
        sa.Column('supplements', sa.Text(), nullable=True),
        sa.Column('medications', sa.Text(), nullable=True),
        sa.Column('diet_type', sa.String(length=50), nullable=True),
        sa.Column('sleep_cycle', sa.String(length=100), nullable=True),
        sa.Column('bmi', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=True, default=datetime.utcnow),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('client_id')
    )
    
    # Create indexes for better query performance
    op.create_index('ix_health_profiles_id', 'health_profiles', ['id'], unique=False)
    op.create_index('ix_health_profiles_client_id', 'health_profiles', ['client_id'], unique=True)
    op.create_index('ix_health_profiles_activity_level', 'health_profiles', ['activity_level'], unique=False)
    op.create_index('ix_health_profiles_diet_type', 'health_profiles', ['diet_type'], unique=False)


def downgrade():
    """Drop health_profiles table and all indexes"""
    
    # Drop indexes first
    op.drop_index('ix_health_profiles_diet_type', table_name='health_profiles')
    op.drop_index('ix_health_profiles_activity_level', table_name='health_profiles')
    op.drop_index('ix_health_profiles_client_id', table_name='health_profiles')
    op.drop_index('ix_health_profiles_id', table_name='health_profiles')
    
    # Drop the table
    op.drop_table('health_profiles')

