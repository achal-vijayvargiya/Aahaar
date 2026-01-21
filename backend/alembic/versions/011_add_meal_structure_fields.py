"""add meal structure fields to platform_clients

Revision ID: 011_meal_structure_fields
Revises: platform_001
Create Date: 2025-01-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '011_meal_structure_fields'
down_revision = 'platform_001'
branch_labels = None
depends_on = None


def upgrade():
    # Add new fields to platform_clients table
    op.add_column('platform_clients', sa.Column('wake_time', sa.String(), nullable=True))
    op.add_column('platform_clients', sa.Column('sleep_time', sa.String(), nullable=True))
    op.add_column('platform_clients', sa.Column('work_schedule_start', sa.String(), nullable=True))
    op.add_column('platform_clients', sa.Column('work_schedule_end', sa.String(), nullable=True))


def downgrade():
    # Remove new fields from platform_clients table
    op.drop_column('platform_clients', 'work_schedule_end')
    op.drop_column('platform_clients', 'work_schedule_start')
    op.drop_column('platform_clients', 'sleep_time')
    op.drop_column('platform_clients', 'wake_time')

