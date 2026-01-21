"""add enriched food models

Revision ID: 008_add_enriched_food_models
Revises: 007_add_agent_chat_history
Create Date: 2025-01-14 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '008_add_enriched_food_models'
down_revision = '007_add_agent_chat_history'
branch_labels = None
depends_on = None


def upgrade():
    # Create enriched_food_items table (main table)
    op.create_table(
        'enriched_food_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('food_id', sa.String(length=100), nullable=True),
        sa.Column('food_name', sa.String(length=200), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('food_type', sa.String(length=100), nullable=True),
        sa.Column('region', sa.String(length=100), nullable=True),
        sa.Column('search_vector', postgresql.TSVECTOR(), nullable=True),
        sa.Column('embedding_id', sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for enriched_food_items
    op.create_index('ix_enriched_food_items_id', 'enriched_food_items', ['id'], unique=False)
    op.create_index('ix_enriched_food_items_food_id', 'enriched_food_items', ['food_id'], unique=True)
    op.create_index('ix_enriched_food_items_food_name', 'enriched_food_items', ['food_name'], unique=False)
    op.create_index('ix_enriched_food_items_category', 'enriched_food_items', ['category'], unique=False)
    op.create_index('ix_enriched_food_items_embedding_id', 'enriched_food_items', ['embedding_id'], unique=True)
    op.create_index('idx_enriched_category_type', 'enriched_food_items', ['category', 'food_type'], unique=False)
    op.create_index('idx_enriched_food_name', 'enriched_food_items', ['food_name'], unique=False)
    op.create_index(
        'idx_enriched_food_search',
        'enriched_food_items',
        ['search_vector'],
        unique=False,
        postgresql_using='gin'
    )
    
    # Create enriched_food_nutrition table
    op.create_table(
        'enriched_food_nutrition',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('food_id', sa.Integer(), nullable=False),
        sa.Column('serving_size_g', sa.Float(), nullable=True, server_default='0'),
        sa.Column('energy_kcal', sa.Float(), nullable=True, server_default='0'),
        sa.Column('calorie_density', sa.Float(), nullable=True, server_default='0'),
        sa.Column('protein_g', sa.Float(), nullable=True, server_default='0'),
        sa.Column('fat_g', sa.Float(), nullable=True, server_default='0'),
        sa.Column('carbs_g', sa.Float(), nullable=True, server_default='0'),
        sa.Column('fiber_g', sa.Float(), nullable=True, server_default='0'),
        sa.Column('sugar_g', sa.Float(), nullable=True, server_default='0'),
        sa.Column('sodium_mg', sa.Float(), nullable=True, server_default='0'),
        sa.Column('glycemic_index', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('glycemic_load', sa.Float(), nullable=True, server_default='0'),
        sa.Column('satiety_index', sa.Float(), nullable=True, server_default='0'),
        sa.ForeignKeyConstraint(['food_id'], ['enriched_food_items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('food_id')
    )
    op.create_index('ix_enriched_food_nutrition_id', 'enriched_food_nutrition', ['id'], unique=False)
    op.create_index('ix_enriched_food_nutrition_food_id', 'enriched_food_nutrition', ['food_id'], unique=True)
    
    # Create enriched_food_micronutrients table
    op.create_table(
        'enriched_food_micronutrients',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('food_id', sa.Integer(), nullable=False),
        sa.Column('calcium_mg', sa.Float(), nullable=True, server_default='0'),
        sa.Column('iron_mg', sa.Float(), nullable=True, server_default='0'),
        sa.Column('magnesium_mg', sa.Float(), nullable=True, server_default='0'),
        sa.Column('potassium_mg', sa.Float(), nullable=True, server_default='0'),
        sa.Column('zinc_mg', sa.Float(), nullable=True, server_default='0'),
        sa.Column('copper_mg', sa.Float(), nullable=True, server_default='0'),
        sa.Column('phosphorus_mg', sa.Float(), nullable=True, server_default='0'),
        sa.Column('manganese_mg', sa.Float(), nullable=True, server_default='0'),
        sa.Column('vitamin_c_mg', sa.Float(), nullable=True, server_default='0'),
        sa.Column('vitamin_d_iu', sa.Float(), nullable=True, server_default='0'),
        sa.Column('vitamin_b_complex', sa.String(length=500), nullable=True),
        sa.Column('folate_mcg', sa.Float(), nullable=True, server_default='0'),
        sa.Column('selenium_mcg', sa.Float(), nullable=True, server_default='0'),
        sa.Column('omega_3_mg', sa.Float(), nullable=True, server_default='0'),
        sa.Column('omega_6_mg', sa.Float(), nullable=True, server_default='0'),
        sa.ForeignKeyConstraint(['food_id'], ['enriched_food_items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('food_id')
    )
    op.create_index('ix_enriched_food_micronutrients_id', 'enriched_food_micronutrients', ['id'], unique=False)
    op.create_index('ix_enriched_food_micronutrients_food_id', 'enriched_food_micronutrients', ['food_id'], unique=True)
    
    # Create enriched_food_ayurveda table
    op.create_table(
        'enriched_food_ayurveda',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('food_id', sa.Integer(), nullable=False),
        sa.Column('dosha_effect_vata', sa.String(length=100), nullable=True),
        sa.Column('dosha_effect_pitta', sa.String(length=100), nullable=True),
        sa.Column('dosha_effect_kapha', sa.String(length=100), nullable=True),
        sa.Column('guna', sa.String(length=50), nullable=True),
        sa.Column('virya', sa.String(length=50), nullable=True),
        sa.Column('vipaka', sa.String(length=50), nullable=True),
        sa.Column('agni_effect', sa.String(length=100), nullable=True),
        sa.Column('digestive_load', sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(['food_id'], ['enriched_food_items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('food_id')
    )
    op.create_index('ix_enriched_food_ayurveda_id', 'enriched_food_ayurveda', ['id'], unique=False)
    op.create_index('ix_enriched_food_ayurveda_food_id', 'enriched_food_ayurveda', ['food_id'], unique=True)
    
    # Create enriched_food_gut_impact table
    op.create_table(
        'enriched_food_gut_impact',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('food_id', sa.Integer(), nullable=False),
        sa.Column('prebiotic_score', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('probiotic_score', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('inflammation_score', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('bloating_risk', sa.String(length=50), nullable=True),
        sa.Column('constipation_risk', sa.String(length=50), nullable=True),
        sa.Column('diarrhea_risk', sa.String(length=50), nullable=True),
        sa.Column('gut_friendly', sa.Boolean(), nullable=True, server_default='false'),
        sa.ForeignKeyConstraint(['food_id'], ['enriched_food_items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('food_id')
    )
    op.create_index('ix_enriched_food_gut_impact_id', 'enriched_food_gut_impact', ['id'], unique=False)
    op.create_index('ix_enriched_food_gut_impact_food_id', 'enriched_food_gut_impact', ['food_id'], unique=True)
    
    # Create enriched_food_disease_suitability table
    op.create_table(
        'enriched_food_disease_suitability',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('food_id', sa.Integer(), nullable=False),
        sa.Column('diabetes', sa.String(length=50), nullable=True),
        sa.Column('hypertension', sa.String(length=50), nullable=True),
        sa.Column('ckd', sa.String(length=50), nullable=True),
        sa.Column('fatty_liver', sa.String(length=50), nullable=True),
        sa.Column('thyroid', sa.String(length=50), nullable=True),
        sa.Column('pcos', sa.String(length=50), nullable=True),
        sa.Column('obesity', sa.String(length=50), nullable=True),
        sa.Column('acidity', sa.String(length=50), nullable=True),
        sa.Column('arthritis', sa.String(length=50), nullable=True),
        sa.Column('heart_disease', sa.String(length=50), nullable=True),
        sa.Column('gastritis', sa.String(length=50), nullable=True),
        sa.Column('ibs', sa.String(length=50), nullable=True),
        sa.Column('ibd', sa.String(length=50), nullable=True),
        sa.Column('anemia', sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(['food_id'], ['enriched_food_items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('food_id')
    )
    op.create_index('ix_enriched_food_disease_suitability_id', 'enriched_food_disease_suitability', ['id'], unique=False)
    op.create_index('ix_enriched_food_disease_suitability_food_id', 'enriched_food_disease_suitability', ['food_id'], unique=True)
    
    # Create enriched_food_allergy_profile table
    op.create_table(
        'enriched_food_allergy_profile',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('food_id', sa.Integer(), nullable=False),
        sa.Column('allergens', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('fodmap_level', sa.String(length=50), nullable=True),
        sa.Column('histamine_level', sa.String(length=50), nullable=True),
        sa.Column('oxalate_level', sa.String(length=50), nullable=True),
        sa.Column('gluten_present', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('lactose_present', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('nightshade', sa.Boolean(), nullable=True, server_default='false'),
        sa.ForeignKeyConstraint(['food_id'], ['enriched_food_items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('food_id')
    )
    op.create_index('ix_enriched_food_allergy_profile_id', 'enriched_food_allergy_profile', ['id'], unique=False)
    op.create_index('ix_enriched_food_allergy_profile_food_id', 'enriched_food_allergy_profile', ['food_id'], unique=True)
    
    # Create enriched_food_interactions table
    op.create_table(
        'enriched_food_interactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('food_id', sa.Integer(), nullable=False),
        sa.Column('medication_interactions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('supplement_interactions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['food_id'], ['enriched_food_items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('food_id')
    )
    op.create_index('ix_enriched_food_interactions_id', 'enriched_food_interactions', ['id'], unique=False)
    op.create_index('ix_enriched_food_interactions_food_id', 'enriched_food_interactions', ['food_id'], unique=True)
    
    # Create enriched_food_goal_suitability table
    op.create_table(
        'enriched_food_goal_suitability',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('food_id', sa.Integer(), nullable=False),
        sa.Column('weight_loss', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('muscle_gain', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('endurance', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('balanced_diet', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('diabetic_weight_loss', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('detox', sa.Integer(), nullable=True, server_default='0'),
        sa.ForeignKeyConstraint(['food_id'], ['enriched_food_items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('food_id')
    )
    op.create_index('ix_enriched_food_goal_suitability_id', 'enriched_food_goal_suitability', ['id'], unique=False)
    op.create_index('ix_enriched_food_goal_suitability_food_id', 'enriched_food_goal_suitability', ['food_id'], unique=True)
    
    # Create enriched_food_contraindications table
    op.create_table(
        'enriched_food_contraindications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('food_id', sa.Integer(), nullable=False),
        sa.Column('avoid_in', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('limit_in', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('safe_in', postgresql.ARRAY(sa.String()), nullable=True),
        sa.ForeignKeyConstraint(['food_id'], ['enriched_food_items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('food_id')
    )
    op.create_index('ix_enriched_food_contraindications_id', 'enriched_food_contraindications', ['id'], unique=False)
    op.create_index('ix_enriched_food_contraindications_food_id', 'enriched_food_contraindications', ['food_id'], unique=True)
    
    # Create enriched_food_descriptions table
    op.create_table(
        'enriched_food_descriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('food_id', sa.Integer(), nullable=False),
        sa.Column('short_description', sa.Text(), nullable=True),
        sa.Column('benefits_text', sa.Text(), nullable=True),
        sa.Column('side_effects_text', sa.Text(), nullable=True),
        sa.Column('ayurveda_text', sa.Text(), nullable=True),
        sa.Column('gut_text', sa.Text(), nullable=True),
        sa.Column('disease_text', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['food_id'], ['enriched_food_items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('food_id')
    )
    op.create_index('ix_enriched_food_descriptions_id', 'enriched_food_descriptions', ['id'], unique=False)
    op.create_index('ix_enriched_food_descriptions_food_id', 'enriched_food_descriptions', ['food_id'], unique=True)


def downgrade():
    # Drop tables in reverse order (child tables first)
    op.drop_index('ix_enriched_food_descriptions_food_id', table_name='enriched_food_descriptions')
    op.drop_index('ix_enriched_food_descriptions_id', table_name='enriched_food_descriptions')
    op.drop_table('enriched_food_descriptions')
    
    op.drop_index('ix_enriched_food_contraindications_food_id', table_name='enriched_food_contraindications')
    op.drop_index('ix_enriched_food_contraindications_id', table_name='enriched_food_contraindications')
    op.drop_table('enriched_food_contraindications')
    
    op.drop_index('ix_enriched_food_goal_suitability_food_id', table_name='enriched_food_goal_suitability')
    op.drop_index('ix_enriched_food_goal_suitability_id', table_name='enriched_food_goal_suitability')
    op.drop_table('enriched_food_goal_suitability')
    
    op.drop_index('ix_enriched_food_interactions_food_id', table_name='enriched_food_interactions')
    op.drop_index('ix_enriched_food_interactions_id', table_name='enriched_food_interactions')
    op.drop_table('enriched_food_interactions')
    
    op.drop_index('ix_enriched_food_allergy_profile_food_id', table_name='enriched_food_allergy_profile')
    op.drop_index('ix_enriched_food_allergy_profile_id', table_name='enriched_food_allergy_profile')
    op.drop_table('enriched_food_allergy_profile')
    
    op.drop_index('ix_enriched_food_disease_suitability_food_id', table_name='enriched_food_disease_suitability')
    op.drop_index('ix_enriched_food_disease_suitability_id', table_name='enriched_food_disease_suitability')
    op.drop_table('enriched_food_disease_suitability')
    
    op.drop_index('ix_enriched_food_gut_impact_food_id', table_name='enriched_food_gut_impact')
    op.drop_index('ix_enriched_food_gut_impact_id', table_name='enriched_food_gut_impact')
    op.drop_table('enriched_food_gut_impact')
    
    op.drop_index('ix_enriched_food_ayurveda_food_id', table_name='enriched_food_ayurveda')
    op.drop_index('ix_enriched_food_ayurveda_id', table_name='enriched_food_ayurveda')
    op.drop_table('enriched_food_ayurveda')
    
    op.drop_index('ix_enriched_food_micronutrients_food_id', table_name='enriched_food_micronutrients')
    op.drop_index('ix_enriched_food_micronutrients_id', table_name='enriched_food_micronutrients')
    op.drop_table('enriched_food_micronutrients')
    
    op.drop_index('ix_enriched_food_nutrition_food_id', table_name='enriched_food_nutrition')
    op.drop_index('ix_enriched_food_nutrition_id', table_name='enriched_food_nutrition')
    op.drop_table('enriched_food_nutrition')
    
    # Drop main table last
    op.drop_index('idx_enriched_food_search', table_name='enriched_food_items', postgresql_using='gin')
    op.drop_index('idx_enriched_food_name', table_name='enriched_food_items')
    op.drop_index('idx_enriched_category_type', table_name='enriched_food_items')
    op.drop_index('ix_enriched_food_items_embedding_id', table_name='enriched_food_items')
    op.drop_index('ix_enriched_food_items_category', table_name='enriched_food_items')
    op.drop_index('ix_enriched_food_items_food_name', table_name='enriched_food_items')
    op.drop_index('ix_enriched_food_items_food_id', table_name='enriched_food_items')
    op.drop_index('ix_enriched_food_items_id', table_name='enriched_food_items')
    op.drop_table('enriched_food_items')

