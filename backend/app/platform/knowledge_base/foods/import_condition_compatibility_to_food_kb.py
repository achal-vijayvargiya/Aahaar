"""
Import Food-Condition Compatibility data to kb_food_condition_compatibility table.

This script creates compatibility records for each food-condition pair based on:
1. MNT profile data (medical_tags, contraindications, preferred_conditions)
2. Medical conditions from medical_conditions_kb_complete.json
3. Nutrition data for portion limits and severity modifiers

Compatibility levels: safe, caution, avoid, contraindicated

Note: Works with or without glycemic_properties. Uses carbs as fallback for diabetes conditions.
When GI values are populated later, re-run this script to update records with more accurate data.

Usage:
    python -m app.platform.knowledge_base.foods.import_condition_compatibility_to_food_kb
    python -m app.platform.knowledge_base.foods.import_condition_compatibility_to_food_kb --dry-run
    python -m app.platform.knowledge_base.foods.import_condition_compatibility_to_food_kb --batch-size 50
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any
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
from app.platform.data.models.kb_food_condition_compatibility import KBFoodConditionCompatibility
from app.utils.logger import logger


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


def determine_compatibility_level(
    condition_id: str,
    medical_tags: Dict[str, bool],
    contraindications: List[str],
    preferred_conditions: List[str],
    macro_compliance: Dict[str, bool],
    micro_compliance: Dict[str, bool],
    nutrition: Optional[KBFoodNutritionBase]
) -> str:
    """
    Determine compatibility level: safe, caution, avoid, contraindicated.
    
    Priority:
    1. If in contraindications → contraindicated
    2. If in preferred_conditions → safe
    3. Check medical_tags for condition → safe/caution/avoid
    4. Default → caution (unknown)
    """
    # Check contraindications first (highest priority)
    if condition_id in contraindications:
        return "contraindicated"
    
    # Check preferred conditions (high priority)
    if condition_id in preferred_conditions:
        return "safe"
    
    # Check medical tags
    tag_mapping = {
        "type_2_diabetes": "diabetic_safe",
        "prediabetes": "prediabetic_safe",
        "cardiovascular_disease": "cardiac_safe",
        "hypertension": "hypertension_safe",
        "ibd": "ibd_safe_remission",
        "ibs": "ibs_safe",
        "gerd": "gerd_safe",
        "gastritis": "gastritis_safe",
        "obesity": "obesity_safe",
        "overweight": "obesity_safe",
        "pcos": "pcos_safe",
        "fatty_liver_disease": "fatty_liver_safe",
        "anemia": "anemia_safe",
        "iron_deficiency_anemia": "anemia_safe",
        "osteoporosis": "osteoporosis_safe",
        "dyslipidemia": "dyslipidemia_safe",
    }
    
    # Special handling for CKD stages
    if condition_id == "ckd":
        if medical_tags.get("renal_safe_stage_3_5", False):
            return "safe"
        elif medical_tags.get("renal_safe_stage_1_2", False):
            return "caution"  # Safe for early stages, caution for later
        else:
            return "avoid"
    
    # Check tag for condition
    tag_name = tag_mapping.get(condition_id)
    if tag_name:
        is_safe = medical_tags.get(tag_name, False)
        if is_safe:
            # For diabetes conditions, check carbs if GI is not available
            if condition_id in ["type_2_diabetes", "prediabetes"]:
                if nutrition and nutrition.macros:
                    carbs_g = safe_float(nutrition.macros.get("carbs_g", 0))
                    # If very high carbs (>50g per 100g), use avoid even if tag says safe
                    if carbs_g > 50:
                        return "avoid"
                    # If high carbs (>30g per 100g), use caution
                    elif carbs_g > 30:
                        return "caution"
            return "safe"
        else:
            return "avoid"
    
    # Default: caution (unknown compatibility)
    return "caution"


def determine_severity_modifier(
    condition_id: str,
    medical_tags: Dict[str, bool],
    nutrition: Optional[KBFoodNutritionBase]
) -> Optional[Dict[str, str]]:
    """
    Determine severity modifier based on condition severity levels.
    
    Returns: { "mild": "safe", "moderate": "caution", "severe": "avoid" }
    """
    # For CKD, severity is based on stage
    if condition_id == "ckd":
        if medical_tags.get("renal_safe_stage_3_5", False):
            return {
                "mild": "safe",
                "moderate": "safe",
                "severe": "caution"
            }
        elif medical_tags.get("renal_safe_stage_1_2", False):
            return {
                "mild": "safe",
                "moderate": "caution",
                "severe": "avoid"
            }
        else:
            return {
                "mild": "caution",
                "moderate": "avoid",
                "severe": "contraindicated"
            }
    
    # For diabetes, severity based on glycemic index OR carbs if GI not available
    if condition_id in ["type_2_diabetes", "prediabetes"]:
        gi = None
        if nutrition and nutrition.glycemic_properties:
            gi = nutrition.glycemic_properties.get("glycemic_index")
        
        if gi is not None:
            # Use GI if available (more accurate)
            if gi < 55:  # Low GI
                return {
                    "mild": "safe",
                    "moderate": "safe",
                    "severe": "caution"
                }
            elif gi < 70:  # Medium GI
                return {
                    "mild": "safe",
                    "moderate": "caution",
                    "severe": "avoid"
                }
            else:  # High GI
                return {
                    "mild": "caution",
                    "moderate": "avoid",
                    "severe": "contraindicated"
                }
        else:
            # Fallback to carbs if GI not available
            if nutrition and nutrition.macros:
                carbs_g = safe_float(nutrition.macros.get("carbs_g", 0))
                if carbs_g < 10:  # Low carb
                    return {
                        "mild": "safe",
                        "moderate": "safe",
                        "severe": "caution"
                    }
                elif carbs_g < 30:  # Medium carb
                    return {
                        "mild": "safe",
                        "moderate": "caution",
                        "severe": "avoid"
                    }
                else:  # High carb
                    return {
                        "mild": "caution",
                        "moderate": "avoid",
                        "severe": "contraindicated"
                    }
            # If no nutrition data, return None (no severity modifier)
            return None
    
    # For hypertension, severity based on sodium
    if condition_id == "hypertension":
        if nutrition and nutrition.micros:
            sodium_mg = safe_float(nutrition.micros.get("sodium_mg", 0))
            if sodium_mg < 100:
                return {
                    "mild": "safe",
                    "moderate": "safe",
                    "severe": "caution"
                }
            elif sodium_mg < 300:
                return {
                    "mild": "safe",
                    "moderate": "caution",
                    "severe": "avoid"
                }
            else:
                return {
                    "mild": "caution",
                    "moderate": "avoid",
                    "severe": "contraindicated"
                }
    
    return None


def determine_portion_limits(
    condition_id: str,
    compatibility: str,
    nutrition: Optional[KBFoodNutritionBase],
    macro_compliance: Dict[str, bool],
    micro_compliance: Dict[str, bool]
) -> Optional[Dict[str, float]]:
    """
    Determine portion limits based on condition and nutrition data.
    
    Returns: { "max_g_per_day": 100, "max_g_per_meal": 50 }
    """
    if compatibility == "contraindicated":
        return None
    
    if compatibility == "avoid":
        return {
            "max_g_per_day": 0,
            "max_g_per_meal": 0
        }
    
    limits = {}
    
    # Diabetes: limit high-carb foods
    if condition_id in ["type_2_diabetes", "prediabetes"]:
        if nutrition and nutrition.macros:
            carbs_g = safe_float(nutrition.macros.get("carbs_g", 0))
            if carbs_g > 30:  # High carb
                limits["max_g_per_day"] = 100
                limits["max_g_per_meal"] = 50
            elif carbs_g > 15:  # Medium carb
                limits["max_g_per_day"] = 200
                limits["max_g_per_meal"] = 100
    
    # Hypertension: limit high-sodium foods
    if condition_id == "hypertension":
        if nutrition and nutrition.micros:
            sodium_mg = safe_float(nutrition.micros.get("sodium_mg", 0))
            if sodium_mg > 300:
                limits["max_g_per_day"] = 50
                limits["max_g_per_meal"] = 25
            elif sodium_mg > 100:
                limits["max_g_per_day"] = 100
                limits["max_g_per_meal"] = 50
    
    # CKD: limit high-potassium/phosphorus foods
    if condition_id == "ckd":
        if nutrition and nutrition.micros:
            potassium_mg = safe_float(nutrition.micros.get("potassium_mg", 0))
            phosphorus_mg = safe_float(nutrition.micros.get("phosphorus_mg", 0))
            if potassium_mg > 200 or phosphorus_mg > 100:
                limits["max_g_per_day"] = 50
                limits["max_g_per_meal"] = 25
    
    # Obesity: limit high-calorie foods
    if condition_id in ["obesity", "overweight"]:
        if nutrition and nutrition.calories_kcal:
            calories = float(nutrition.calories_kcal)
            if calories > 300:  # High calorie density
                limits["max_g_per_day"] = 100
                limits["max_g_per_meal"] = 50
    
    return limits if limits else None


def determine_preparation_notes(
    condition_id: str,
    compatibility: str,
    nutrition: Optional[KBFoodNutritionBase]
) -> Optional[str]:
    """Determine preparation notes based on condition."""
    notes = []
    
    if condition_id == "ckd":
        if nutrition and nutrition.micros:
            potassium_mg = safe_float(nutrition.micros.get("potassium_mg", 0))
            if potassium_mg > 200:
                notes.append("Soak or boil to reduce potassium content")
    
    if condition_id in ["type_2_diabetes", "prediabetes"]:
        if nutrition:
            # Check if high GI or high carbs
            gi = None
            if nutrition.glycemic_properties:
                gi = nutrition.glycemic_properties.get("glycemic_index")
            
            carbs_g = safe_float(nutrition.macros.get("carbs_g", 0)) if nutrition.macros else 0
            
            if (gi and gi > 55) or (gi is None and carbs_g > 15):
                notes.append("Combine with protein and fiber to reduce glycemic impact")
    
    if condition_id == "gerd":
        notes.append("Avoid spicy preparation; prefer steamed or boiled")
    
    if condition_id == "gastritis":
        notes.append("Avoid fried or spicy preparation; prefer bland cooking methods")
    
    return "; ".join(notes) if notes else None


def get_source_reference(condition_id: str, medical_conditions: List[Dict[str, Any]]) -> str:
    """Get source reference for condition."""
    for condition in medical_conditions:
        if condition.get("condition_id") == condition_id:
            return condition.get("source_reference", "")
    return ""


def import_condition_compatibility(
    db: Session,
    batch_size: int = 50,
    dry_run: bool = False
) -> Dict[str, int]:
    """Import food-condition compatibility records."""
    stats = {
        "total_foods": 0,
        "total_conditions": 0,
        "processed": 0,
        "created": 0,
        "updated": 0,
        "skipped_no_mnt_profile": 0,
        "errors": 0,
    }
    
    # Load medical conditions
    logger.info("Loading medical conditions...")
    medical_conditions = load_medical_conditions()
    condition_ids = [c.get("condition_id") for c in medical_conditions if c.get("status") == "active"]
    stats["total_conditions"] = len(condition_ids)
    logger.info(f"Loaded {len(condition_ids)} active medical conditions")
    
    # Get all foods with MNT profiles
    foods = db.query(KBFoodMaster).join(KBFoodMNTProfile).all()
    stats["total_foods"] = len(foods)
    
    total_records = len(foods) * len(condition_ids)
    logger.info(f"Processing {len(foods)} foods × {len(condition_ids)} conditions = {total_records} compatibility records...")
    
    for idx, food in enumerate(foods):
        try:
            mnt_profile = food.mnt_profile
            if not mnt_profile:
                stats["skipped_no_mnt_profile"] += 1
                continue
            
            nutrition = food.nutrition
            medical_tags = mnt_profile.medical_tags or {}
            contraindications = mnt_profile.contraindications or []
            preferred_conditions = mnt_profile.preferred_conditions or []
            macro_compliance = mnt_profile.macro_compliance or {}
            micro_compliance = mnt_profile.micro_compliance or {}
            
            # Create compatibility record for each condition
            for condition_id in condition_ids:
                # Determine compatibility level
                compatibility = determine_compatibility_level(
                    condition_id,
                    medical_tags,
                    contraindications,
                    preferred_conditions,
                    macro_compliance,
                    micro_compliance,
                    nutrition
                )
                
                # Determine severity modifier
                severity_modifier = determine_severity_modifier(
                    condition_id,
                    medical_tags,
                    nutrition
                )
                
                # Determine portion limits
                portion_limit = determine_portion_limits(
                    condition_id,
                    compatibility,
                    nutrition,
                    macro_compliance,
                    micro_compliance
                )
                
                # Determine preparation notes
                preparation_notes = determine_preparation_notes(
                    condition_id,
                    compatibility,
                    nutrition
                )
                
                # Get source reference
                source_ref = get_source_reference(condition_id, medical_conditions)
                
                # Check if record exists
                existing = db.query(KBFoodConditionCompatibility).filter(
                    KBFoodConditionCompatibility.food_id == food.food_id,
                    KBFoodConditionCompatibility.condition_id == condition_id
                ).first()
                
                if existing:
                    # Update existing
                    existing.compatibility = compatibility
                    existing.severity_modifier = severity_modifier
                    existing.portion_limit = portion_limit
                    existing.preparation_notes = preparation_notes
                    existing.source_reference = source_ref
                    
                    if not dry_run:
                        db.add(existing)
                    
                    stats["updated"] += 1
                else:
                    # Create new
                    new_compatibility = KBFoodConditionCompatibility(
                        food_id=food.food_id,
                        condition_id=condition_id,
                        compatibility=compatibility,
                        severity_modifier=severity_modifier,
                        portion_limit=portion_limit,
                        preparation_notes=preparation_notes,
                        source="MNT Rules KB",
                        source_reference=source_ref,
                        version="1.0",
                        status="active"
                    )
                    
                    if not dry_run:
                        db.add(new_compatibility)
                    
                    stats["created"] += 1
                
                stats["processed"] += 1
                
                # Commit periodically
                if stats["processed"] % batch_size == 0 and not dry_run:
                    db.commit()
                    logger.info(f"Processed {stats['processed']}/{total_records} compatibility records...")
        
        except Exception as e:
            logger.error(f"Error processing {food.food_id}: {e}", exc_info=True)
            stats["errors"] += 1
            continue
    
    if not dry_run:
        db.commit()
    
    return stats


def main():
    parser = argparse.ArgumentParser(description="Import food-condition compatibility to food KB")
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size for commits")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    
    args = parser.parse_args()
    
    db = SessionLocal()
    
    try:
        stats = import_condition_compatibility(db, args.batch_size, args.dry_run)
        
        logger.info("=" * 70)
        logger.info("SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Total foods: {stats['total_foods']}")
        logger.info(f"Total conditions: {stats['total_conditions']}")
        logger.info(f"Total records processed: {stats['processed']}")
        logger.info(f"Created: {stats['created']}")
        logger.info(f"Updated: {stats['updated']}")
        logger.info(f"Skipped (no MNT profile): {stats['skipped_no_mnt_profile']}")
        logger.info(f"Errors: {stats['errors']}")
        logger.info("=" * 70)
        logger.info("Note: This script works with or without glycemic_properties.")
        logger.info("When GI values are populated, re-run this script to update records.")
        logger.info("=" * 70)
        
    finally:
        db.close()


if __name__ == "__main__":
    main()

