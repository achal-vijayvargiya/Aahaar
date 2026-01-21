-- COMPLETE QUERY TO CHECK ALL FOODS RETURNED BY FOOD ENGINE
-- Shows all foods in 'pulse' category with their filter status
-- Based on test profile: T2D Weight Loss (type_2_diabetes, max carb 45%, max sodium 2300mg)
-- This query replicates the exact filtering logic used by Food Engine

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
        fm.status = 'active'
        AND fe.exchange_category = 'pulse'  -- All pulse category foods
),
tier1_exclusions AS (
    -- Direct food exclusions
    SELECT food_id, 'direct_food_exclusion' as reason
    FROM base_foods
    WHERE food_id IN ('canned_foods', 'fried_foods', 'full_fat_dairy', 'high_gi_foods', 'high_saturated_fat_foods')
    
    UNION
    
    -- Condition contraindicated
    SELECT 
        fcc.food_id,
        'condition_contraindicated' as reason
    FROM kb_food_condition_compatibility fcc
    WHERE 
        fcc.food_id IN (SELECT food_id FROM base_foods)
        AND fcc.condition_id IN ('type_2_diabetes', 'diabetes')
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
        AND (
            'type_2_diabetes' = ANY(bf.contraindications)
            OR 'diabetes' = ANY(bf.contraindications)
        )
    
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
    -- Extreme sodium (>5x daily max = >11500mg per 100g for 2300mg limit)
    SELECT 
        food_id,
        'extremely_high_sodium_unsafe' as reason
    FROM base_foods
    WHERE sodium_mg > 11500
    
    UNION
    
    -- Extreme carb (>95% carbs)
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
ORDER BY 
    CASE 
        WHEN t1.reason IS NOT NULL THEN 1
        WHEN t2.reason IS NOT NULL THEN 2
        ELSE 3
    END,
    bf.display_name;

