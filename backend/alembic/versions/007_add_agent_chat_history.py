"""add agent chat history

Revision ID: 007_add_agent_chat_history
Revises: 006_add_enhanced_food_kb
Create Date: 2025-01-10 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '007_add_agent_chat_history'
down_revision = '006_enhanced_food_kb'
branch_labels = None
depends_on = None


def upgrade():
    # Create agent_chat_sessions table
    op.create_table(
        'agent_chat_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(length=100), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('doctor_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('stage', sa.String(length=50), nullable=True),
        sa.Column('diet_plan_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['doctor_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['diet_plan_id'], ['diet_plans.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_agent_chat_sessions_session_id', 'agent_chat_sessions', ['session_id'], unique=True)
    op.create_index('ix_agent_chat_sessions_client_id', 'agent_chat_sessions', ['client_id'])
    op.create_index('ix_agent_chat_sessions_doctor_id', 'agent_chat_sessions', ['doctor_id'])
    
    # Create agent_chat_history table
    op.create_table(
        'agent_chat_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('doctor_id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(length=100), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('tool_calls', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('intermediate_steps', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('context_snapshot', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['doctor_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_agent_chat_history_client_id', 'agent_chat_history', ['client_id'])
    op.create_index('ix_agent_chat_history_session_id', 'agent_chat_history', ['session_id'])
    op.create_index('ix_agent_chat_history_created_at', 'agent_chat_history', ['created_at'])
    op.create_index('idx_client_session', 'agent_chat_history', ['client_id', 'session_id'])
    op.create_index('idx_session_created', 'agent_chat_history', ['session_id', 'created_at'])


def downgrade():
    op.drop_table('agent_chat_history')
    op.drop_table('agent_chat_sessions')

