"""add diet plans

Revision ID: 005
Revises: 004
Create Date: 2025-11-02 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create diet_plans and diet_plan_meals tables."""
    
    # Create diet_plans table
    op.create_table(
        'diet_plans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('duration_days', sa.Integer(), nullable=True),
        sa.Column('start_date', sa.DateTime(), nullable=True),
        sa.Column('end_date', sa.DateTime(), nullable=True),
        sa.Column('health_goals', sa.Text(), nullable=True),
        sa.Column('dosha_type', sa.String(length=50), nullable=True),
        sa.Column('diet_type', sa.String(length=50), nullable=True),
        sa.Column('allergies', sa.Text(), nullable=True),
        sa.Column('target_calories', sa.Float(), nullable=True),
        sa.Column('target_protein_g', sa.Float(), nullable=True),
        sa.Column('target_carbs_g', sa.Float(), nullable=True),
        sa.Column('target_fat_g', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_diet_plans_id'), 'diet_plans', ['id'], unique=False)
    op.create_index(op.f('ix_diet_plans_client_id'), 'diet_plans', ['client_id'], unique=False)
    
    # Create diet_plan_meals table
    op.create_table(
        'diet_plan_meals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('diet_plan_id', sa.Integer(), nullable=False),
        sa.Column('day_number', sa.Integer(), nullable=False),
        sa.Column('meal_time', sa.String(length=20), nullable=False),
        sa.Column('meal_type', sa.String(length=50), nullable=False),
        sa.Column('food_dish', sa.Text(), nullable=False),
        sa.Column('food_item_ids', sa.Text(), nullable=True),
        sa.Column('healing_purpose', sa.Text(), nullable=True),
        sa.Column('portion', sa.String(length=100), nullable=True),
        sa.Column('dosha_notes', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('calories', sa.Float(), nullable=True),
        sa.Column('protein_g', sa.Float(), nullable=True),
        sa.Column('carbs_g', sa.Float(), nullable=True),
        sa.Column('fat_g', sa.Float(), nullable=True),
        sa.Column('order_in_day', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['diet_plan_id'], ['diet_plans.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_diet_plan_meals_id'), 'diet_plan_meals', ['id'], unique=False)
    op.create_index(op.f('ix_diet_plan_meals_diet_plan_id'), 'diet_plan_meals', ['diet_plan_id'], unique=False)


def downgrade() -> None:
    """Drop diet plan tables."""
    op.drop_index(op.f('ix_diet_plan_meals_diet_plan_id'), table_name='diet_plan_meals')
    op.drop_index(op.f('ix_diet_plan_meals_id'), table_name='diet_plan_meals')
    op.drop_table('diet_plan_meals')
    
    op.drop_index(op.f('ix_diet_plans_client_id'), table_name='diet_plans')
    op.drop_index(op.f('ix_diet_plans_id'), table_name='diet_plans')
    op.drop_table('diet_plans')

