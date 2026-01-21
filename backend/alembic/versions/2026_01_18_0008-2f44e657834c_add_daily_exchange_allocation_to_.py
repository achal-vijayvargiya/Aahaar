"""add_daily_exchange_allocation_to_exchange_allocations

Revision ID: 2f44e657834c
Revises: ab6f352019a6
Create Date: 2026-01-18 00:08:56.839083

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '2f44e657834c'
down_revision: Union[str, None] = 'ab6f352019a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add daily_exchange_allocation column to platform_exchange_allocations table
    op.add_column(
        'platform_exchange_allocations',
        sa.Column('daily_exchange_allocation', postgresql.JSONB(), nullable=True)
    )


def downgrade() -> None:
    # Remove daily_exchange_allocation column
    op.drop_column('platform_exchange_allocations', 'daily_exchange_allocation')

