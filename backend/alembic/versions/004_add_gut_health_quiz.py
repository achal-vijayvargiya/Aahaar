"""Add gut health quiz table

Revision ID: 004
Revises: 003
Create Date: 2025-11-02 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003_food'
branch_labels = None
depends_on = None


def upgrade():
    """Create gut_health_quizzes table"""
    
    # Create the gut_health_quizzes table
    op.create_table(
        'gut_health_quizzes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        
        # Quiz responses (GQ1-GQ10)
        sa.Column('gq1_appetite', sa.String(length=1), nullable=False),
        sa.Column('gq2_digestion', sa.String(length=1), nullable=False),
        sa.Column('gq3_bowel', sa.String(length=1), nullable=False),
        sa.Column('gq4_post_meal', sa.String(length=1), nullable=False),
        sa.Column('gq5_food_reaction', sa.String(length=1), nullable=False),
        sa.Column('gq6_tongue_breath', sa.String(length=1), nullable=False),
        sa.Column('gq7_sleep', sa.String(length=1), nullable=False),
        sa.Column('gq8_eating_habit', sa.String(length=1), nullable=False),
        sa.Column('gq9_bloating', sa.String(length=1), nullable=False),
        sa.Column('gq10_immunity', sa.String(length=1), nullable=False),
        
        # Calculated scores
        sa.Column('balanced_score', sa.Integer(), nullable=False),
        sa.Column('weak_score', sa.Integer(), nullable=False),
        sa.Column('overactive_score', sa.Integer(), nullable=False),
        sa.Column('gut_health_state', sa.String(length=50), nullable=False),
        
        # Notes and timestamps
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=True, default=datetime.utcnow),
        
        # Constraints
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for better query performance
    op.create_index('ix_gut_health_quizzes_id', 'gut_health_quizzes', ['id'], unique=False)
    op.create_index('ix_gut_health_quizzes_client_id', 'gut_health_quizzes', ['client_id'], unique=False)
    op.create_index('ix_gut_health_quizzes_state', 'gut_health_quizzes', ['gut_health_state'], unique=False)
    op.create_index('ix_gut_health_quizzes_created_at', 'gut_health_quizzes', ['created_at'], unique=False)
    
    # Composite index for client + date (for getting latest quiz)
    op.create_index('idx_gut_health_client_created', 'gut_health_quizzes', ['client_id', 'created_at'], unique=False)


def downgrade():
    """Drop gut_health_quizzes table and all indexes"""
    
    # Drop indexes first
    op.drop_index('idx_gut_health_client_created', table_name='gut_health_quizzes')
    op.drop_index('ix_gut_health_quizzes_created_at', table_name='gut_health_quizzes')
    op.drop_index('ix_gut_health_quizzes_state', table_name='gut_health_quizzes')
    op.drop_index('ix_gut_health_quizzes_client_id', table_name='gut_health_quizzes')
    op.drop_index('ix_gut_health_quizzes_id', table_name='gut_health_quizzes')
    
    # Drop the table
    op.drop_table('gut_health_quizzes')

