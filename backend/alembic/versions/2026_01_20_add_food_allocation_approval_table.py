"""add_food_allocation_approval_table

Revision ID: add_food_allocation_approval
Revises: 2f44e657834c
Create Date: 2026-01-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid


# revision identifiers, used by Alembic.
revision: str = 'add_food_allocation_approval'
down_revision: Union[str, None] = '2f44e657834c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create platform_food_allocation_approvals table
    op.create_table(
        'platform_food_allocation_approvals',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('assessment_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('platform_assessments.id'), nullable=False),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('platform_diet_plans.id'), nullable=True),
        sa.Column('day_number', sa.String(), nullable=False),
        sa.Column('meal_name', sa.String(), nullable=False),
        sa.Column('is_approved', sa.Boolean(), default=False, nullable=False),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('notes', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.utcnow()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.utcnow(), onupdate=sa.func.utcnow()),
    )
    
    # Create indexes
    op.create_index('ix_platform_food_allocation_approvals_assessment_id', 'platform_food_allocation_approvals', ['assessment_id'])
    op.create_index('ix_platform_food_allocation_approvals_plan_id', 'platform_food_allocation_approvals', ['plan_id'])
    op.create_index('ix_platform_food_allocation_approvals_day_meal', 'platform_food_allocation_approvals', ['assessment_id', 'day_number', 'meal_name'], unique=True)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_platform_food_allocation_approvals_day_meal', 'platform_food_allocation_approvals')
    op.drop_index('ix_platform_food_allocation_approvals_plan_id', 'platform_food_allocation_approvals')
    op.drop_index('ix_platform_food_allocation_approvals_assessment_id', 'platform_food_allocation_approvals')
    
    # Drop table
    op.drop_table('platform_food_allocation_approvals')
