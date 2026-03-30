"""add_platform_programs_and_week_index

Revision ID: add_platform_programs
Revises: add_food_allocation_approval
Create Date: 2026-01-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid


revision: str = 'add_platform_programs'
down_revision: Union[str, None] = 'add_food_allocation_approval'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create platform_programs table
    op.create_table(
        'platform_programs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('platform_clients.id'), nullable=False),
        sa.Column('assessment_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('platform_assessments.id'), nullable=False),
        sa.Column('duration_weeks', sa.Integer(), nullable=False),
        sa.Column('current_week', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('goal', postgresql.JSONB(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.utcnow()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.utcnow(), onupdate=sa.func.utcnow()),
    )
    op.create_index('ix_platform_programs_id', 'platform_programs', ['id'])
    op.create_index('ix_platform_programs_client_id', 'platform_programs', ['client_id'])
    op.create_index('ix_platform_programs_assessment_id', 'platform_programs', ['assessment_id'])

    # Add program_id and week_index to platform_diet_plans
    op.add_column('platform_diet_plans', sa.Column('program_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('platform_diet_plans', sa.Column('week_index', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_platform_diet_plans_program_id',
        'platform_diet_plans',
        'platform_programs',
        ['program_id'],
        ['id'],
    )
    op.create_index('ix_platform_diet_plans_program_id', 'platform_diet_plans', ['program_id'])
    op.create_index('ix_platform_diet_plans_program_week', 'platform_diet_plans', ['program_id', 'week_index'])


def downgrade() -> None:
    op.drop_index('ix_platform_diet_plans_program_week', 'platform_diet_plans')
    op.drop_index('ix_platform_diet_plans_program_id', 'platform_diet_plans')
    op.drop_constraint('fk_platform_diet_plans_program_id', 'platform_diet_plans', type_='foreignkey')
    op.drop_column('platform_diet_plans', 'week_index')
    op.drop_column('platform_diet_plans', 'program_id')

    op.drop_index('ix_platform_programs_assessment_id', 'platform_programs')
    op.drop_index('ix_platform_programs_client_id', 'platform_programs')
    op.drop_index('ix_platform_programs_id', 'platform_programs')
    op.drop_table('platform_programs')
