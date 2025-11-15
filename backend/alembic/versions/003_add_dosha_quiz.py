"""Add dosha quiz table

Revision ID: 003
Revises: 002
Create Date: 2025-11-02 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    """Create dosha_quizzes table"""
    
    # Create the dosha_quizzes table
    op.create_table(
        'dosha_quizzes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        
        # Quiz responses (Q1-Q10)
        sa.Column('q1_body_frame', sa.String(length=1), nullable=False),
        sa.Column('q2_skin_type', sa.String(length=1), nullable=False),
        sa.Column('q3_hair_type', sa.String(length=1), nullable=False),
        sa.Column('q4_appetite', sa.String(length=1), nullable=False),
        sa.Column('q5_sleep', sa.String(length=1), nullable=False),
        sa.Column('q6_personality', sa.String(length=1), nullable=False),
        sa.Column('q7_stress', sa.String(length=1), nullable=False),
        sa.Column('q8_climate', sa.String(length=1), nullable=False),
        sa.Column('q9_energy', sa.String(length=1), nullable=False),
        sa.Column('q10_mind', sa.String(length=1), nullable=False),
        
        # Calculated scores
        sa.Column('vata_score', sa.Integer(), nullable=False),
        sa.Column('pitta_score', sa.Integer(), nullable=False),
        sa.Column('kapha_score', sa.Integer(), nullable=False),
        sa.Column('dominant_dosha', sa.String(length=50), nullable=False),
        
        # Notes and timestamps
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=True, default=datetime.utcnow),
        
        # Constraints
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for better query performance
    op.create_index('ix_dosha_quizzes_id', 'dosha_quizzes', ['id'], unique=False)
    op.create_index('ix_dosha_quizzes_client_id', 'dosha_quizzes', ['client_id'], unique=False)
    op.create_index('ix_dosha_quizzes_dominant_dosha', 'dosha_quizzes', ['dominant_dosha'], unique=False)
    op.create_index('ix_dosha_quizzes_created_at', 'dosha_quizzes', ['created_at'], unique=False)
    
    # Composite index for client + date (for getting latest quiz)
    op.create_index('idx_client_created', 'dosha_quizzes', ['client_id', 'created_at'], unique=False)


def downgrade():
    """Drop dosha_quizzes table and all indexes"""
    
    # Drop indexes first
    op.drop_index('idx_client_created', table_name='dosha_quizzes')
    op.drop_index('ix_dosha_quizzes_created_at', table_name='dosha_quizzes')
    op.drop_index('ix_dosha_quizzes_dominant_dosha', table_name='dosha_quizzes')
    op.drop_index('ix_dosha_quizzes_client_id', table_name='dosha_quizzes')
    op.drop_index('ix_dosha_quizzes_id', table_name='dosha_quizzes')
    
    # Drop the table
    op.drop_table('dosha_quizzes')

