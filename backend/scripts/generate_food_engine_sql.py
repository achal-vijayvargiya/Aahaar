"""
Generate SQL query for Food Engine debugging.
This script generates the exact SQL query that Food Engine would run for a given exchange category.
"""
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import text
from app.database import SessionLocal
from app.platform.data.models.kb_food_master import KBFoodMaster
from app.platform.data.models.kb_food_exchange_profile import KBFoodExchangeProfile
from app.platform.data.models.kb_food_nutrition_base import KBFoodNutritionBase
from app.platform.data.models.kb_food_mnt_profile import KBFoodMNTProfile
from app.platform.data.models.kb_food_condition_compatibility import KBFoodConditionCompatibility


def generate_food_engine_sql(
    exchange_category: str = "pulse",
    food_exclusions: list = None,
    medical_conditions: list = None
):
    """
    Generate SQL query that matches Food Engine's query logic.
    
    Args:
        exchange_category: Exchange category to filter (default: "pulse")
        food_exclusions: List of food IDs to exclude
        medical_conditions: List of medical condition IDs
    """
    if food_exclusions is None:
        food_exclusions = [
            "canned_foods",
            "fried_foods", 
            "full_fat_dairy",
            "high_gi_foods",
            "high_saturated_fat_foods"
        ]
    
    if medical_conditions is None:
        medical_conditions = ["type_2_diabetes", "diabetes"]
    
    # Build the SQL query matching Food Engine's logic
    sql_query = f"""
-- Food Engine Base Query (matching kb_food_adapter.py lines 293-304)
-- This is the query that gets ALL foods for the exchange category
SELECT 
    fm.food_id,
    fm.display_name,
    fm.status,
    fe.exchange_category,
    fn.calories_kcal,
    fn.macros->>'carbs_g' as carbs_g,
    fn.macros->>'protein_g' as protein_g,
    fn.micros->>'sodium_mg' as sodium_mg,
    fe.serving_size_per_exchange_g,
    fmnt.contraindications,
    fmnt.medical_tags,
    fmnt.food_exclusion_tags,
    fmnt.macro_compliance,
    fmnt.micro_compliance
FROM kb_food_master fm
INNER JOIN kb_food_exchange_profile fe 
    ON fm.food_id = fe.food_id
INNER JOIN kb_food_nutrition_base fn 
    ON fm.food_id = fn.food_id
LEFT OUTER JOIN kb_food_mnt_profile fmnt 
    ON fm.food_id = fmnt.food_id
WHERE 
    fm.status = 'active'
    AND fe.exchange_category = '{exchange_category}'
ORDER BY fm.display_name;
"""
    
    # Tier 1 Hard Exclusion Checks
    tier1_checks = f"""
-- TIER 1 HARD EXCLUSION CHECKS (NEVER BYPASSED)
-- These checks are applied in Python after fetching results

-- 1. Direct Food ID Exclusions
-- Check if food_id is in: {food_exclusions}
-- SQL equivalent:
SELECT food_id, display_name, 'direct_food_exclusion' as exclusion_reason
FROM kb_food_master
WHERE food_id IN ({', '.join([f"'{ex}'" for ex in food_exclusions])});

-- 2. Condition Compatibility (Contraindicated Only)
-- Check kb_food_condition_compatibility for compatibility = 'contraindicated'
SELECT 
    fcc.food_id,
    fm.display_name,
    fcc.condition_id,
    fcc.compatibility,
    'condition_contraindicated' as exclusion_reason
FROM kb_food_condition_compatibility fcc
JOIN kb_food_master fm ON fcc.food_id = fm.food_id
WHERE 
    fcc.condition_id IN ({', '.join([f"'{c}'" for c in medical_conditions])})
    AND fcc.compatibility = 'contraindicated'
    AND fcc.status = 'active';

-- 3. MNT Profile Contraindications
-- Check if user condition matches contraindications array
SELECT 
    fm.food_id,
    fm.display_name,
    fmnt.contraindications,
    'mnt_profile_contraindication' as exclusion_reason
FROM kb_food_master fm
JOIN kb_food_mnt_profile fmnt ON fm.food_id = fmnt.food_id
WHERE 
    fmnt.contraindications IS NOT NULL
    AND ({' OR '.join([f"'{c}' = ANY(fmnt.contraindications)" for c in medical_conditions])});

-- 4. Diabetes Safety Flags (diabetic_safe = false)
SELECT 
    fm.food_id,
    fm.display_name,
    fmnt.medical_tags->>'diabetic_safe' as diabetic_safe,
    'diabetic_safe_false' as exclusion_reason
FROM kb_food_master fm
JOIN kb_food_mnt_profile fmnt ON fm.food_id = fmnt.food_id
WHERE 
    fmnt.medical_tags->>'diabetic_safe' = 'false';
"""
    
    # Tier 2 Soft Constraint Checks
    tier2_checks = f"""
-- TIER 2 SOFT CONSTRAINT CHECKS (Can be relaxed for variety)
-- These are now simplified - only extreme values are excluded

-- 1. Extreme Sodium Check (>5x daily max = >11500mg per 100g for 2300mg limit)
SELECT 
    fm.food_id,
    fm.display_name,
    (fn.micros->>'sodium_mg')::float as sodium_mg,
    'extremely_high_sodium_unsafe' as exclusion_reason
FROM kb_food_master fm
JOIN kb_food_nutrition_base fn ON fm.food_id = fn.food_id
JOIN kb_food_exchange_profile fe ON fm.food_id = fe.food_id
WHERE 
    fe.exchange_category = '{exchange_category}'
    AND (fn.micros->>'sodium_mg')::float > 11500;  -- 5x 2300mg

-- 2. Extreme Carb Check (>95% carbs)
SELECT 
    fm.food_id,
    fm.display_name,
    fn.calories_kcal,
    (fn.macros->>'carbs_g')::float as carbs_g,
    CASE 
        WHEN fn.calories_kcal > 0 
        THEN ((fn.macros->>'carbs_g')::float * 4 / fn.calories_kcal) * 100
        ELSE 0
    END as carb_pct,
    'extremely_high_carb_unsafe' as exclusion_reason
FROM kb_food_master fm
JOIN kb_food_nutrition_base fn ON fm.food_id = fn.food_id
JOIN kb_food_exchange_profile fe ON fm.food_id = fe.food_id
WHERE 
    fe.exchange_category = '{exchange_category}'
    AND fn.calories_kcal > 0
    AND ((fn.macros->>'carbs_g')::float * 4 / fn.calories_kcal) * 100 > 95;
"""
    
    # Complete Query for Soybean specifically
    soybean_query = f"""
-- COMPLETE QUERY TO CHECK WHY SOYBEAN PASSES FILTERS
-- Check soybean (B024 and B025) against all filters

WITH base_foods AS (
    SELECT 
        fm.food_id,
        fm.display_name,
        fm.status,
        fe.exchange_category,
        fn.calories_kcal,
        (fn.macros->>'carbs_g')::float as carbs_g,
        (fn.macros->>'protein_g')::float as protein_g,
        (fn.micros->>'sodium_mg')::float as sodium_mg,
        fe.serving_size_per_exchange_g,
        fmnt.contraindications,
        fmnt.medical_tags,
        fmnt.food_exclusion_tags,
        fmnt.macro_compliance,
        fmnt.micro_compliance
    FROM kb_food_master fm
    INNER JOIN kb_food_exchange_profile fe ON fm.food_id = fe.food_id
    INNER JOIN kb_food_nutrition_base fn ON fm.food_id = fn.food_id
    LEFT OUTER JOIN kb_food_mnt_profile fmnt ON fm.food_id = fmnt.food_id
    WHERE 
        fm.food_id IN ('B024', 'B025')  -- Soybean brown and white
        AND fm.status = 'active'
        AND fe.exchange_category = '{exchange_category}'
),
tier1_exclusions AS (
    -- Direct food exclusions
    SELECT food_id, 'direct_food_exclusion' as reason
    FROM base_foods
    WHERE food_id IN ({', '.join([f"'{ex}'" for ex in food_exclusions])})
    
    UNION
    
    -- Condition contraindicated
    SELECT 
        fcc.food_id,
        'condition_contraindicated' as reason
    FROM kb_food_condition_compatibility fcc
    WHERE 
        fcc.food_id IN ('B024', 'B025')
        AND fcc.condition_id IN ({', '.join([f"'{c}'" for c in medical_conditions])})
        AND fcc.compatibility = 'contraindicated'
        AND fcc.status = 'active'
    
    UNION
    
    -- MNT contraindications
    SELECT 
        bf.food_id,
        'mnt_profile_contraindication' as reason
    FROM base_foods bf
    WHERE 
        bf.contraindications IS NOT NULL
        AND ({' OR '.join([f"'{c}' = ANY(bf.contraindications)" for c in medical_conditions])})
    
    UNION
    
    -- Diabetic safe = false
    SELECT 
        bf.food_id,
        'diabetic_safe_false' as reason
    FROM base_foods bf
    WHERE 
        bf.medical_tags->>'diabetic_safe' = 'false'
),
tier2_exclusions AS (
    -- Extreme sodium
    SELECT 
        food_id,
        'extremely_high_sodium_unsafe' as reason
    FROM base_foods
    WHERE sodium_mg > 11500
    
    UNION
    
    -- Extreme carb
    SELECT 
        food_id,
        'extremely_high_carb_unsafe' as reason
    FROM base_foods
    WHERE 
        calories_kcal > 0
        AND (carbs_g * 4 / calories_kcal) * 100 > 95
)
SELECT 
    bf.*,
    t1.reason as tier1_exclusion_reason,
    t2.reason as tier2_exclusion_reason,
    CASE 
        WHEN t1.reason IS NOT NULL THEN 'EXCLUDED (Tier 1)'
        WHEN t2.reason IS NOT NULL THEN 'EXCLUDED (Tier 2)'
        ELSE 'PASSES ALL FILTERS'
    END as filter_status,
    -- Calculate carb percentage
    CASE 
        WHEN bf.calories_kcal > 0 
        THEN ROUND((bf.carbs_g * 4 / bf.calories_kcal) * 100, 2)
        ELSE 0
    END as carb_percentage,
    -- Check compliance flags
    bf.macro_compliance->>'low_carb_friendly' as low_carb_friendly,
    bf.macro_compliance->>'moderate_carb_friendly' as moderate_carb_friendly,
    bf.medical_tags->>'diabetic_safe' as diabetic_safe,
    bf.medical_tags->>'glycemic_classification' as glycemic_classification
FROM base_foods bf
LEFT JOIN tier1_exclusions t1 ON bf.food_id = t1.food_id
LEFT JOIN tier2_exclusions t2 ON bf.food_id = t2.food_id
ORDER BY bf.food_id;
"""
    
    return {
        "base_query": sql_query,
        "tier1_checks": tier1_checks,
        "tier2_checks": tier2_checks,
        "soybean_complete_query": soybean_query
    }


def main():
    """Generate and print SQL queries."""
    print("=" * 80)
    print("FOOD ENGINE SQL QUERY GENERATOR")
    print("=" * 80)
    print()
    
    # Test profile data from e2e test
    exchange_category = "pulse"
    food_exclusions = [
        "canned_foods",
        "fried_foods",
        "full_fat_dairy",
        "high_gi_foods",
        "high_saturated_fat_foods"
    ]
    medical_conditions = ["type_2_diabetes", "diabetes"]
    
    queries = generate_food_engine_sql(
        exchange_category=exchange_category,
        food_exclusions=food_exclusions,
        medical_conditions=medical_conditions
    )
    
    print("1. BASE QUERY (Gets all foods for exchange category)")
    print("-" * 80)
    print(queries["base_query"])
    print()
    
    print("2. TIER 1 HARD EXCLUSION CHECKS")
    print("-" * 80)
    print(queries["tier1_checks"])
    print()
    
    print("3. TIER 2 SOFT CONSTRAINT CHECKS")
    print("-" * 80)
    print(queries["tier2_checks"])
    print()
    
    print("4. COMPLETE QUERY FOR SOYBEAN (B024, B025)")
    print("-" * 80)
    print(queries["soybean_complete_query"])
    print()
    
    print("=" * 80)
    print("INSTRUCTIONS:")
    print("=" * 80)
    print("1. Copy the 'COMPLETE QUERY FOR SOYBEAN' above")
    print("2. Run it in your PostgreSQL database")
    print("3. Check the 'filter_status' column to see why soybean passes")
    print("4. Review tier1_exclusion_reason and tier2_exclusion_reason columns")
    print()


if __name__ == "__main__":
    main()

