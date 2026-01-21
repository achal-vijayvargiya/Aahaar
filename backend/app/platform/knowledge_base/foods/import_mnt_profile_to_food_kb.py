"""
Import MNT Profile data to kb_food_mnt_profile table.

This script calculates MNT compliance flags, medical safety tags, and exclusion/inclusion
tags for all foods based on:
1. Nutrition data from kb_food_nutrition_base
2. MNT rules from mnt_rules_kb_complete.json
3. Medical conditions from medical_conditions_kb_complete.json

All fields are DERIVED (computed) - never manually edited.

Usage:
    python -m app.platform.knowledge_base.foods.import_mnt_profile_to_food_kb
    python -m app.platform.knowledge_base.foods.import_mnt_profile_to_food_kb --dry-run
    python -m app.platform.knowledge_base.foods.import_mnt_profile_to_food_kb --batch-size 50
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from decimal import Decimal

# Add backend directory to path
backend_dir = Path(__file__).parent.parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.platform.data.models.kb_food_master import KBFoodMaster
from app.platform.data.models.kb_food_nutrition_base import KBFoodNutritionBase
from app.platform.data.models.kb_food_mnt_profile import KBFoodMNTProfile
from app.utils.logger import logger


# Thresholds for compliance flags (per 100g)
MACRO_THRESHOLDS = {
    "low_carb": 10.0,  # g per 100g
    "moderate_carb_max": 30.0,  # g per 100g
    "high_fiber": 5.0,  # g per 100g
    "low_fat": 10.0,  # g per 100g
    "high_protein": 15.0,  # g per 100g
    "low_saturated_fat": 3.0,  # g per 100g
    "low_added_sugar": 5.0,  # g per 100g
    "high_monounsaturated_fat": 5.0,  # g per 100g
    "omega_3_rich": 0.5,  # g per 100g (500mg)
}

MICRO_THRESHOLDS = {
    "low_sodium": 100.0,  # mg per 100g
    "low_potassium": 200.0,  # mg per 100g (for renal)
    "low_phosphorus": 100.0,  # mg per 100g (for renal)
    "iron_rich": 2.0,  # mg per 100g
    "calcium_rich": 100.0,  # mg per 100g
    "selenium_rich": 20.0,  # mcg per 100g
    "folate_rich": 50.0,  # mcg per 100g
    "vitamin_c_rich": 30.0,  # mg per 100g
    "vitamin_d_rich": 2.0,  # mcg per 100g (or 80 IU)
    "vitamin_b12_rich": 1.0,  # mcg per 100g
    "magnesium_rich": 50.0,  # mg per 100g
    "vitamin_e_rich": 2.0,  # mg per 100g
}

# Medical condition to MNT rule mapping
CONDITION_TO_RULES = {
    "type_2_diabetes": ["mnt_carb_restriction_diabetes", "mnt_glycemic_control_type1_diabetes"],
    "prediabetes": ["mnt_prediabetes_prevention", "mnt_carb_restriction_diabetes"],
    "gestational_diabetes": ["mnt_carb_restriction_diabetes"],
    "hypertension": ["mnt_sodium_restriction_hypertension"],
    "metabolic_syndrome": ["mnt_sodium_restriction_hypertension", "mnt_fat_modification_dyslipidemia"],
    "dyslipidemia": ["mnt_fat_modification_dyslipidemia"],
    "obesity": ["mnt_calorie_restriction_obesity"],
    "overweight": ["mnt_calorie_restriction_obesity"],
    "pcos": ["mnt_pcos_metabolic_management"],
    "ckd": ["mnt_ckd_renal_restrictions"],
    "fatty_liver_disease": ["mnt_fatty_liver_sugar_reduction"],
    "cardiovascular_disease": ["mnt_cardiovascular_heart_health"],
    "anemia": ["mnt_generic_anemia_support"],
    "iron_deficiency_anemia": ["mnt_iron_deficiency_anemia_repletion"],
    "osteoporosis": ["mnt_bone_health_osteoporosis"],
    "ibs": ["mnt_low_fodmap_ibs"],
    "ibd": ["mnt_ibd_anti_inflammatory_nutrition"],
    "gerd": ["mnt_gerd_reflux_control"],
    "gastritis": ["mnt_gastritis_gastric_healing"],
    "hypothyroidism": ["mnt_hypothyroidism_micronutrient_support"],
}


def load_mnt_rules() -> List[Dict[str, Any]]:
    """Load MNT rules from JSON file."""
    rules_path = Path(__file__).parent.parent / "mnt_rules" / "mnt_rules_kb_complete.json"
    with open(rules_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_medical_conditions() -> List[Dict[str, Any]]:
    """Load medical conditions from JSON file."""
    conditions_path = Path(__file__).parent.parent / "medical" / "medical_conditions_kb_complete.json"
    with open(conditions_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def safe_float(value: Any) -> float:
    """Safely convert value to float, returning 0.0 if None or invalid."""
    if value is None:
        return 0.0
    try:
        if isinstance(value, Decimal):
            return float(value)
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def calculate_macro_compliance(macros: Dict[str, Any], calories_kcal: Optional[float]) -> Dict[str, bool]:
    """Calculate macro compliance flags from nutrition data."""
    compliance = {}
    
    carbs_g = safe_float(macros.get("carbs_g", 0))
    fiber_g = safe_float(macros.get("fiber_g", 0))
    fat_g = safe_float(macros.get("fat_g", 0))
    protein_g = safe_float(macros.get("protein_g", 0))
    saturated_fat_g = safe_float(macros.get("saturated_fat_g", 0))
    trans_fat_g = safe_float(macros.get("trans_fat_g", 0))
    added_sugar_g = safe_float(macros.get("added_sugar_g", 0))
    monounsaturated_fat_g = safe_float(macros.get("monounsaturated_fat_g", 0))
    omega_3_mg = safe_float(macros.get("omega_3_mg", 0))
    omega_3_g = omega_3_mg / 1000.0  # Convert mg to g
    
    # Low carb friendly: < 10g per 100g
    compliance["low_carb_friendly"] = carbs_g < MACRO_THRESHOLDS["low_carb"]
    
    # Moderate carb friendly: 10-30g per 100g
    compliance["moderate_carb_friendly"] = (
        carbs_g >= MACRO_THRESHOLDS["low_carb"] and 
        carbs_g <= MACRO_THRESHOLDS["moderate_carb_max"]
    )
    
    # High fiber: >= 5g per 100g
    compliance["high_fiber"] = fiber_g >= MACRO_THRESHOLDS["high_fiber"]
    
    # Low fat: < 10g per 100g
    compliance["low_fat"] = fat_g < MACRO_THRESHOLDS["low_fat"]
    
    # High protein: >= 15g per 100g
    compliance["high_protein"] = protein_g >= MACRO_THRESHOLDS["high_protein"]
    
    # Low saturated fat: < 3g per 100g
    compliance["low_saturated_fat"] = saturated_fat_g < MACRO_THRESHOLDS["low_saturated_fat"]
    
    # Zero trans fat: = 0
    compliance["zero_trans_fat"] = trans_fat_g == 0.0
    
    # Low added sugar: < 5g per 100g
    compliance["low_added_sugar"] = added_sugar_g < MACRO_THRESHOLDS["low_added_sugar"]
    
    # High monounsaturated fat: > 5g per 100g
    compliance["high_monounsaturated_fat"] = monounsaturated_fat_g > MACRO_THRESHOLDS["high_monounsaturated_fat"]
    
    # Omega-3 rich: > 0.5g per 100g
    compliance["omega_3_rich"] = omega_3_g > MACRO_THRESHOLDS["omega_3_rich"]
    
    return compliance


def calculate_micro_compliance(micros: Dict[str, Any]) -> Dict[str, bool]:
    """Calculate micro compliance flags from nutrition data."""
    compliance = {}
    
    sodium_mg = safe_float(micros.get("sodium_mg", 0))
    potassium_mg = safe_float(micros.get("potassium_mg", 0))
    phosphorus_mg = safe_float(micros.get("phosphorus_mg", 0))
    iron_mg = safe_float(micros.get("iron_mg", 0))
    calcium_mg = safe_float(micros.get("calcium_mg", 0))
    selenium_mcg = safe_float(micros.get("selenium_mcg", 0))
    folate_mcg = safe_float(micros.get("folate_mcg", 0))
    vitamin_c_mg = safe_float(micros.get("vitamin_c_mg", 0))
    vitamin_d_iu = safe_float(micros.get("vitamin_d_iu", 0))
    vitamin_d_mcg = vitamin_d_iu / 40.0 if vitamin_d_iu > 0 else 0.0  # Convert IU to mcg (1 IU = 0.025 mcg)
    vitamin_b12_mcg = safe_float(micros.get("vitamin_b12_mcg", 0))
    magnesium_mg = safe_float(micros.get("magnesium_mg", 0))
    vitamin_e_mg = safe_float(micros.get("vitamin_e_mg", 0))
    
    # Low sodium: < 100mg per 100g
    compliance["low_sodium"] = sodium_mg < MICRO_THRESHOLDS["low_sodium"]
    
    # Low potassium: < 200mg per 100g (for renal diets)
    compliance["low_potassium"] = potassium_mg < MICRO_THRESHOLDS["low_potassium"]
    
    # Low phosphorus: < 100mg per 100g (for renal diets)
    compliance["low_phosphorus"] = phosphorus_mg < MICRO_THRESHOLDS["low_phosphorus"]
    
    # Iron rich: >= 2mg per 100g
    compliance["iron_rich"] = iron_mg >= MICRO_THRESHOLDS["iron_rich"]
    
    # Calcium rich: >= 100mg per 100g
    compliance["calcium_rich"] = calcium_mg >= MICRO_THRESHOLDS["calcium_rich"]
    
    # Selenium rich: >= 20mcg per 100g
    compliance["selenium_rich"] = selenium_mcg >= MICRO_THRESHOLDS["selenium_rich"]
    
    # Folate rich: >= 50mcg per 100g
    compliance["folate_rich"] = folate_mcg >= MICRO_THRESHOLDS["folate_rich"]
    
    # Vitamin C rich: >= 30mg per 100g
    compliance["vitamin_c_rich"] = vitamin_c_mg >= MICRO_THRESHOLDS["vitamin_c_rich"]
    
    # Vitamin D rich: >= 2mcg per 100g (or 80 IU)
    compliance["vitamin_d_rich"] = vitamin_d_mcg >= MICRO_THRESHOLDS["vitamin_d_rich"]
    
    # Vitamin B12 rich: >= 1mcg per 100g
    compliance["vitamin_b12_rich"] = vitamin_b12_mcg >= MICRO_THRESHOLDS["vitamin_b12_rich"]
    
    # Magnesium rich: >= 50mg per 100g
    compliance["magnesium_rich"] = magnesium_mg >= MICRO_THRESHOLDS["magnesium_rich"]
    
    # Vitamin E rich: >= 2mg per 100g
    compliance["vitamin_e_rich"] = vitamin_e_mg >= MICRO_THRESHOLDS["vitamin_e_rich"]
    
    return compliance


def check_mnt_constraint_compliance(
    rule: Dict[str, Any],
    macros: Dict[str, Any],
    micros: Dict[str, Any],
    calories_kcal: Optional[float],
    glycemic_properties: Optional[Dict[str, Any]]
) -> bool:
    """Check if food complies with MNT rule constraints."""
    macro_constraints = rule.get("macro_constraints", {})
    micro_constraints = rule.get("micro_constraints", {})
    
    # Check macro constraints
    for constraint_key, constraint_value in macro_constraints.items():
        if constraint_key == "carbohydrates_percent":
            max_pct = constraint_value.get("max")
            if max_pct is not None and calories_kcal and calories_kcal > 0:
                carbs_g = safe_float(macros.get("carbs_g", 0))
                carb_pct = (carbs_g * 4 / calories_kcal) * 100
                if carb_pct > max_pct + 5:  # Allow 5% tolerance
                    return False
        
        elif constraint_key == "fiber_g":
            min_g = constraint_value.get("min")
            if min_g is not None:
                fiber_g = safe_float(macros.get("fiber_g", 0))
                # This is daily requirement, not per 100g - skip per-food check
                pass
        
        elif constraint_key == "saturated_fat_percent":
            max_pct = constraint_value.get("max")
            if max_pct is not None and calories_kcal and calories_kcal > 0:
                sat_fat_g = safe_float(macros.get("saturated_fat_g", 0))
                sat_fat_pct = (sat_fat_g * 9 / calories_kcal) * 100
                if sat_fat_pct > max_pct + 2:  # Allow 2% tolerance
                    return False
        
        elif constraint_key == "trans_fat_g":
            max_g = constraint_value.get("max")
            if max_g is not None:
                trans_fat_g = safe_float(macros.get("trans_fat_g", 0))
                if trans_fat_g > max_g:
                    return False
        
        elif constraint_key == "added_sugars_percent":
            max_pct = constraint_value.get("max")
            if max_pct is not None and calories_kcal and calories_kcal > 0:
                added_sugar_g = safe_float(macros.get("added_sugar_g", 0))
                added_sugar_pct = (added_sugar_g * 4 / calories_kcal) * 100
                if added_sugar_pct > max_pct + 1:  # Allow 1% tolerance
                    return False
    
    # Check micro constraints
    for constraint_key, constraint_value in micro_constraints.items():
        if constraint_key == "sodium_mg":
            max_mg = constraint_value.get("max")
            if max_mg is not None:
                # This is daily limit, but we check per 100g: if > 500mg per 100g, likely high sodium
                sodium_mg = safe_float(micros.get("sodium_mg", 0))
                if sodium_mg > 500:  # High sodium food threshold
                    return False
        
        elif constraint_key == "potassium_mg":
            max_mg = constraint_value.get("max")
            if max_mg is not None:
                potassium_mg = safe_float(micros.get("potassium_mg", 0))
                if potassium_mg > 300:  # High potassium food threshold
                    return False
        
        elif constraint_key == "phosphorus_mg":
            max_mg = constraint_value.get("max")
            if max_mg is not None:
                phosphorus_mg = safe_float(micros.get("phosphorus_mg", 0))
                if phosphorus_mg > 200:  # High phosphorus food threshold
                    return False
    
    return True


def match_food_tags(
    food_name: str,
    food_category: Optional[str],
    exclusion_tags: List[str],
    inclusion_tags: List[str]
) -> tuple[List[str], List[str]]:
    """Match food name/category against MNT rule exclusion/inclusion tags."""
    matched_exclusions = []
    matched_inclusions = []
    
    food_name_lower = food_name.lower()
    category_lower = (food_category or "").lower()
    
    # Simple keyword matching
    tag_mappings = {
        "refined_sugar": ["sugar", "jaggery", "honey", "syrup", "sweet"],
        "white_flour": ["white flour", "maida", "refined flour"],
        "high_gi_foods": ["white rice", "white bread", "potato"],
        "sweetened_beverages": ["juice", "soda", "cola", "drink"],
        "processed_snacks": ["chips", "namkeen", "biscuit", "cookie"],
        "whole_grains": ["brown rice", "whole wheat", "oats", "quinoa", "millet", "bajra", "jowar", "ragi"],
        "fiber_rich_foods": ["dal", "legume", "bean", "lentil", "chickpea"],
        "low_gi_foods": ["brown rice", "oats", "quinoa", "lentil"],
        "processed_foods": ["processed", "canned", "packaged"],
        "high_sodium_foods": ["pickle", "papad", "salted"],
        "trans_fats": ["margarine", "shortening", "vanaspati"],
        "high_saturated_fat_foods": ["butter", "ghee", "cream", "lard"],
        "fried_foods": ["fried", "deep fried"],
        "processed_meats": ["sausage", "bacon", "ham"],
        "full_fat_dairy": ["full cream", "whole milk"],
        "omega_3_rich_foods": ["fish", "salmon", "mackerel", "walnut", "flaxseed"],
        "monounsaturated_fats": ["olive oil", "avocado", "almond", "peanut"],
        "plant_based_fats": ["coconut oil", "sesame oil"],
        "nutrient_dense_foods": ["vegetable", "fruit", "nut", "seed"],
        "low_calorie_high_volume_foods": ["cucumber", "lettuce", "spinach", "tomato"],
        "iron_rich_foods": ["spinach", "dal", "lentil", "chickpea", "meat", "fish"],
        "calcium_rich_foods": ["milk", "yogurt", "cheese", "paneer", "sesame"],
        "vitamin_d_sources": ["fish", "egg", "mushroom"],
        "selenium_rich_foods": ["brazil nut", "fish", "egg"],
        "b12_rich_foods": ["meat", "fish", "egg", "dairy"],
        "folate_rich_foods": ["spinach", "dal", "lentil", "chickpea"],
        "low_fodmap_fruits": ["banana", "blueberry", "strawberry", "orange"],
        "low_fodmap_vegetables": ["carrot", "cucumber", "lettuce", "spinach"],
        "high_fodmap_foods": ["onion", "garlic", "apple", "mango", "wheat"],
        "spicy_foods": ["chili", "pepper", "spicy"],
        "caffeine": ["coffee", "tea", "caffeine"],
        "alcohol": ["alcohol", "beer", "wine"],
        "citrus_fruits": ["orange", "lemon", "lime", "grapefruit"],
        "carbonated_beverages": ["soda", "cola", "fizzy"],
        "chocolate": ["chocolate"],
        "excess_raw_cruciferous_vegetables": ["cabbage", "broccoli", "cauliflower"],
    }
    
    # Check exclusions
    for exclusion_tag in exclusion_tags:
        keywords = tag_mappings.get(exclusion_tag, [exclusion_tag.replace("_", " ")])
        for keyword in keywords:
            if keyword in food_name_lower or keyword in category_lower:
                matched_exclusions.append(exclusion_tag)
                break
    
    # Check inclusions
    for inclusion_tag in inclusion_tags:
        keywords = tag_mappings.get(inclusion_tag, [inclusion_tag.replace("_", " ")])
        for keyword in keywords:
            if keyword in food_name_lower or keyword in category_lower:
                matched_inclusions.append(inclusion_tag)
                break
    
    return list(set(matched_exclusions)), list(set(matched_inclusions))


def evaluate_medical_tags(
    food_name: str,
    food_category: Optional[str],
    macros: Dict[str, Any],
    micros: Dict[str, Any],
    calories_kcal: Optional[float],
    glycemic_properties: Optional[Dict[str, Any]],
    mnt_rules: List[Dict[str, Any]]
) -> Dict[str, bool]:
    """Evaluate medical safety tags by checking against MNT rules."""
    tags = {}
    
    # Map condition IDs to tag names
    condition_to_tag = {
        "type_2_diabetes": "diabetic_safe",
        "prediabetes": "prediabetic_safe",
        "cardiovascular_disease": "cardiac_safe",
        "hypertension": "hypertension_safe",
        "ckd": "renal_safe_stage_1_2",  # Will check stage 3-5 separately
        "ibd": "ibd_safe_remission",
        "ibs": "ibs_safe",
        "gerd": "gerd_safe",
        "gastritis": "gastritis_safe",
        "obesity": "obesity_safe",
        "pcos": "pcos_safe",
        "fatty_liver_disease": "fatty_liver_safe",
        "anemia": "anemia_safe",
        "iron_deficiency_anemia": "anemia_safe",
        "osteoporosis": "osteoporosis_safe",
        "dyslipidemia": "dyslipidemia_safe",
    }
    
    # Get all exclusion and inclusion tags from all rules
    all_exclusions = set()
    all_inclusions = set()
    for rule in mnt_rules:
        all_exclusions.update(rule.get("food_exclusions", []))
        all_inclusions.update(rule.get("food_inclusions", []))
    
    # Check food tags
    matched_exclusions, matched_inclusions = match_food_tags(
        food_name, food_category, list(all_exclusions), list(all_inclusions)
    )
    
    # Evaluate each condition
    for condition_id, tag_name in condition_to_tag.items():
        rule_ids = CONDITION_TO_RULES.get(condition_id, [])
        if not rule_ids:
            tags[tag_name] = True  # Default safe if no rules
            continue
        
        # Check if food matches any exclusion for this condition
        is_excluded = False
        for rule in mnt_rules:
            if rule.get("rule_id") in rule_ids:
                rule_exclusions = rule.get("food_exclusions", [])
                if any(exc in matched_exclusions for exc in rule_exclusions):
                    is_excluded = True
                    break
        
        if is_excluded:
            tags[tag_name] = False
            continue
        
        # Check constraint compliance
        is_compliant = True
        for rule in mnt_rules:
            if rule.get("rule_id") in rule_ids:
                if not check_mnt_constraint_compliance(
                    rule, macros, micros, calories_kcal, glycemic_properties
                ):
                    is_compliant = False
                    break
        
        tags[tag_name] = is_compliant
    
    # Special handling for CKD stages
    potassium_mg = safe_float(micros.get("potassium_mg", 0))
    phosphorus_mg = safe_float(micros.get("phosphorus_mg", 0))
    sodium_mg = safe_float(micros.get("sodium_mg", 0))
    
    tags["renal_safe_stage_1_2"] = (
        tags.get("renal_safe_stage_1_2", True) and
        potassium_mg < 400 and
        phosphorus_mg < 300 and
        sodium_mg < 500
    )
    
    tags["renal_safe_stage_3_5"] = (
        potassium_mg < MICRO_THRESHOLDS["low_potassium"] and
        phosphorus_mg < MICRO_THRESHOLDS["low_phosphorus"] and
        sodium_mg < 300
    )
    
    return tags


def determine_contraindications(
    medical_tags: Dict[str, bool],
    matched_exclusions: List[str],
    micros: Dict[str, Any]
) -> List[str]:
    """Determine contraindications based on medical tags and exclusions."""
    contraindications = []
    
    # Check medical tags
    if not medical_tags.get("renal_safe_stage_3_5", True):
        contraindications.append("ckd_stage_3_5")
    
    if not medical_tags.get("renal_safe_stage_1_2", True):
        contraindications.append("ckd_stage_1_2")
    
    # High potassium contraindications
    potassium_mg = safe_float(micros.get("potassium_mg", 0))
    if potassium_mg > 300:
        if "ckd_stage_3_5" not in contraindications:
            contraindications.append("ckd_stage_3_5")
    
    # High phosphorus contraindications
    phosphorus_mg = safe_float(micros.get("phosphorus_mg", 0))
    if phosphorus_mg > 200:
        if "ckd_stage_3_5" not in contraindications:
            contraindications.append("ckd_stage_3_5")
    
    return list(set(contraindications))


def determine_preferred_conditions(
    macro_compliance: Dict[str, bool],
    micro_compliance: Dict[str, bool],
    medical_tags: Dict[str, bool],
    matched_inclusions: List[str],
    mnt_rules: List[Dict[str, Any]]
) -> List[str]:
    """Determine preferred conditions where food is particularly beneficial."""
    preferred = []
    
    # Map inclusion tags and compliance to conditions
    if "whole_grains" in matched_inclusions or "fiber_rich_foods" in matched_inclusions:
        if medical_tags.get("diabetic_safe", False):
            preferred.append("type_2_diabetes")
            preferred.append("prediabetes")
    
    if macro_compliance.get("low_carb_friendly", False):
        preferred.append("type_2_diabetes")
        preferred.append("prediabetes")
    
    if macro_compliance.get("high_fiber", False):
        preferred.append("type_2_diabetes")
        preferred.append("prediabetes")
        preferred.append("inadequate_fiber_intake")
    
    if macro_compliance.get("low_fat", False) and macro_compliance.get("low_saturated_fat", False):
        preferred.append("obesity")
        preferred.append("overweight")
        preferred.append("cardiovascular_disease")
    
    if macro_compliance.get("high_protein", False):
        preferred.append("inadequate_protein_intake")
        preferred.append("obesity")
    
    if micro_compliance.get("iron_rich", False):
        preferred.append("anemia")
        preferred.append("iron_deficiency_anemia")
    
    if micro_compliance.get("calcium_rich", False):
        preferred.append("osteoporosis")
    
    if micro_compliance.get("low_sodium", False):
        preferred.append("hypertension")
        preferred.append("metabolic_syndrome")
    
    if macro_compliance.get("omega_3_rich", False):
        preferred.append("cardiovascular_disease")
        preferred.append("dyslipidemia")
    
    if "low_gi_foods" in matched_inclusions:
        preferred.append("type_2_diabetes")
        preferred.append("prediabetes")
        preferred.append("pcos")
    
    return list(set(preferred))


def calculate_mnt_profile(
    food: KBFoodMaster,
    nutrition: KBFoodNutritionBase,
    mnt_rules: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Calculate complete MNT profile for a food."""
    macros = nutrition.macros or {}
    micros = nutrition.micros or {}
    calories_kcal = float(nutrition.calories_kcal) if nutrition.calories_kcal else None
    glycemic_properties = nutrition.glycemic_properties or {}
    
    # Calculate compliance flags
    macro_compliance = calculate_macro_compliance(macros, calories_kcal)
    micro_compliance = calculate_micro_compliance(micros)
    
    # Get all exclusion/inclusion tags
    all_exclusions = set()
    all_inclusions = set()
    for rule in mnt_rules:
        all_exclusions.update(rule.get("food_exclusions", []))
        all_inclusions.update(rule.get("food_inclusions", []))
    
    # Match food tags
    matched_exclusions, matched_inclusions = match_food_tags(
        food.display_name, food.category, list(all_exclusions), list(all_inclusions)
    )
    
    # Evaluate medical tags
    medical_tags = evaluate_medical_tags(
        food.display_name,
        food.category,
        macros,
        micros,
        calories_kcal,
        glycemic_properties,
        mnt_rules
    )
    
    # Determine contraindications and preferred conditions
    contraindications = determine_contraindications(medical_tags, matched_exclusions, micros)
    preferred_conditions = determine_preferred_conditions(
        macro_compliance, micro_compliance, medical_tags, matched_inclusions, mnt_rules
    )
    
    return {
        "macro_compliance": macro_compliance,
        "micro_compliance": micro_compliance,
        "medical_tags": medical_tags,
        "food_exclusion_tags": matched_exclusions,
        "food_inclusion_tags": matched_inclusions,
        "contraindications": contraindications,
        "preferred_conditions": preferred_conditions,
    }


def import_mnt_profiles(
    db: Session,
    batch_size: int = 50,
    dry_run: bool = False
) -> Dict[str, int]:
    """Import MNT profiles for all foods."""
    stats = {
        "total_foods": 0,
        "processed": 0,
        "updated": 0,
        "created": 0,
        "skipped_no_nutrition": 0,
        "errors": 0,
    }
    
    # Load MNT rules
    logger.info("Loading MNT rules...")
    mnt_rules = load_mnt_rules()
    logger.info(f"Loaded {len(mnt_rules)} MNT rules")
    
    # Get all foods with nutrition data
    foods = db.query(KBFoodMaster).join(KBFoodNutritionBase).all()
    stats["total_foods"] = len(foods)
    
    logger.info(f"Processing {len(foods)} foods...")
    
    for idx, food in enumerate(foods):
        try:
            nutrition = food.nutrition
            if not nutrition:
                stats["skipped_no_nutrition"] += 1
                continue
            
            # Calculate MNT profile
            profile_data = calculate_mnt_profile(food, nutrition, mnt_rules)
            
            # Check if profile exists
            existing_profile = db.query(KBFoodMNTProfile).filter(
                KBFoodMNTProfile.food_id == food.food_id
            ).first()
            
            if existing_profile:
                # Update existing
                existing_profile.macro_compliance = profile_data["macro_compliance"]
                existing_profile.micro_compliance = profile_data["micro_compliance"]
                existing_profile.medical_tags = profile_data["medical_tags"]
                existing_profile.food_exclusion_tags = profile_data["food_exclusion_tags"]
                existing_profile.food_inclusion_tags = profile_data["food_inclusion_tags"]
                existing_profile.contraindications = profile_data["contraindications"]
                existing_profile.preferred_conditions = profile_data["preferred_conditions"]
                
                if not dry_run:
                    db.add(existing_profile)
                
                stats["updated"] += 1
            else:
                # Create new
                new_profile = KBFoodMNTProfile(
                    food_id=food.food_id,
                    macro_compliance=profile_data["macro_compliance"],
                    micro_compliance=profile_data["micro_compliance"],
                    medical_tags=profile_data["medical_tags"],
                    food_exclusion_tags=profile_data["food_exclusion_tags"],
                    food_inclusion_tags=profile_data["food_inclusion_tags"],
                    contraindications=profile_data["contraindications"],
                    preferred_conditions=profile_data["preferred_conditions"],
                )
                
                if not dry_run:
                    db.add(new_profile)
                
                stats["created"] += 1
            
            stats["processed"] += 1
            
            # Commit periodically
            if stats["processed"] % batch_size == 0 and not dry_run:
                db.commit()
                logger.info(f"Processed {stats['processed']}/{stats['total_foods']} foods...")
        
        except Exception as e:
            logger.error(f"Error processing {food.food_id}: {e}", exc_info=True)
            stats["errors"] += 1
            continue
    
    if not dry_run:
        db.commit()
    
    return stats


def main():
    parser = argparse.ArgumentParser(description="Import MNT profiles to food KB")
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size for commits")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    
    args = parser.parse_args()
    
    db = SessionLocal()
    
    try:
        stats = import_mnt_profiles(db, args.batch_size, args.dry_run)
        
        logger.info("=" * 70)
        logger.info("SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Total foods: {stats['total_foods']}")
        logger.info(f"Processed: {stats['processed']}")
        logger.info(f"Created: {stats['created']}")
        logger.info(f"Updated: {stats['updated']}")
        logger.info(f"Skipped (no nutrition): {stats['skipped_no_nutrition']}")
        logger.info(f"Errors: {stats['errors']}")
        logger.info("=" * 70)
        
    finally:
        db.close()


if __name__ == "__main__":
    main()

