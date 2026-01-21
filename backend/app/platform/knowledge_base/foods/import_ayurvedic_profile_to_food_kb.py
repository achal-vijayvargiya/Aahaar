"""
Import Ayurvedic Profile data to kb_food_ayurvedic_profile table.

This script creates Ayurvedic profiles for all foods using rule-based inference.
Uses food category, name, and nutrition data to determine Ayurvedic properties.

Note: This is rule-based inference (~60-70% accuracy). Can be refined later with LLM
for food-specific accuracy.

Usage:
    python -m app.platform.knowledge_base.foods.import_ayurvedic_profile_to_food_kb
    python -m app.platform.knowledge_base.foods.import_ayurvedic_profile_to_food_kb --dry-run
    python -m app.platform.knowledge_base.foods.import_ayurvedic_profile_to_food_kb --batch-size 50
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
from app.platform.data.models.kb_food_ayurvedic_profile import KBFoodAyurvedicProfile
from app.utils.logger import logger


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


# Category-based Ayurvedic property mappings
CATEGORY_TO_DOSHA_EFFECTS = {
    "cereals_and_millets": {
        "vata": "pacifying",
        "pitta": "neutral",
        "kapha": "neutral_to_aggravating"
    },
    "grain_legumes": {
        "vata": "pacifying",
        "pitta": "pacifying",
        "kapha": "neutral"
    },
    "fruits": {
        "vata": "pacifying",
        "pitta": "pacifying",
        "kapha": "neutral_to_aggravating"
    },
    "green_leafy_vegetables": {
        "vata": "neutral",
        "pitta": "pacifying",
        "kapha": "pacifying"
    },
    "other_vegetables": {
        "vata": "neutral",
        "pitta": "neutral",
        "kapha": "neutral"
    },
    "roots_and_tubers": {
        "vata": "pacifying",
        "pitta": "neutral",
        "kapha": "aggravating"
    },
    "nuts_and_oil_seeds": {
        "vata": "pacifying",
        "pitta": "neutral_to_aggravating",
        "kapha": "aggravating"
    },
    "animal_meat": {
        "vata": "pacifying",
        "pitta": "aggravating",
        "kapha": "aggravating"
    },
    "poultry": {
        "vata": "pacifying",
        "pitta": "neutral_to_aggravating",
        "kapha": "neutral"
    },
    "marine_fish": {
        "vata": "pacifying",
        "pitta": "aggravating",
        "kapha": "aggravating"
    },
}

CATEGORY_TO_RASA = {
    "cereals_and_millets": ["sweet"],
    "grain_legumes": ["sweet", "astringent"],
    "fruits": ["sweet"],
    "green_leafy_vegetables": ["bitter", "astringent"],
    "other_vegetables": ["sweet", "bitter"],
    "roots_and_tubers": ["sweet"],
    "nuts_and_oil_seeds": ["sweet"],
    "animal_meat": ["sweet"],
    "poultry": ["sweet"],
    "marine_fish": ["sweet"],
}

CATEGORY_TO_VIRYA = {
    "cereals_and_millets": "cooling",
    "grain_legumes": "cooling",
    "fruits": "cooling",
    "green_leafy_vegetables": "cooling",
    "other_vegetables": "cooling",
    "roots_and_tubers": "heating",
    "nuts_and_oil_seeds": "heating",
    "animal_meat": "heating",
    "poultry": "heating",
    "marine_fish": "heating",
}

CATEGORY_TO_VIPAKA = {
    "cereals_and_millets": "sweet",
    "grain_legumes": "sweet",
    "fruits": "sweet",
    "green_leafy_vegetables": "pungent",
    "other_vegetables": "sweet",
    "roots_and_tubers": "sweet",
    "nuts_and_oil_seeds": "sweet",
    "animal_meat": "sour",
    "poultry": "sour",
    "marine_fish": "sour",
}

CATEGORY_TO_GUNA = {
    "cereals_and_millets": "sattvic",
    "grain_legumes": "sattvic",
    "fruits": "sattvic",
    "green_leafy_vegetables": "sattvic",
    "other_vegetables": "sattvic",
    "roots_and_tubers": "sattvic",
    "nuts_and_oil_seeds": "sattvic",
    "animal_meat": "tamasic",
    "poultry": "rajasic",
    "marine_fish": "rajasic",
}

CATEGORY_TO_DIGESTIVE_LOAD = {
    "cereals_and_millets": "moderate",
    "grain_legumes": "light",
    "fruits": "light",
    "green_leafy_vegetables": "light",
    "other_vegetables": "light",
    "roots_and_tubers": "moderate",
    "nuts_and_oil_seeds": "heavy",
    "animal_meat": "heavy",
    "poultry": "moderate",
    "marine_fish": "moderate",
}

CATEGORY_TO_AGNI_EFFECT = {
    "cereals_and_millets": "neutral",
    "grain_legumes": "improving",
    "fruits": "neutral",
    "green_leafy_vegetables": "improving",
    "other_vegetables": "neutral",
    "roots_and_tubers": "neutral",
    "nuts_and_oil_seeds": "neutral",
    "animal_meat": "diminishing",
    "poultry": "neutral",
    "marine_fish": "neutral",
}

# Food name keyword refinements
FOOD_KEYWORD_REFINEMENTS = {
    # Specific foods with known properties
    "moong": {"dosha_effects": {"vata": "pacifying", "pitta": "pacifying", "kapha": "neutral"}, "rasa": ["sweet", "astringent"], "virya": "cooling", "digestive_load": "light", "agni_effect": "improving"},
    "dal": {"dosha_effects": {"vata": "pacifying", "pitta": "pacifying", "kapha": "neutral"}, "rasa": ["sweet", "astringent"], "virya": "cooling", "digestive_load": "light"},
    "lentil": {"dosha_effects": {"vata": "pacifying", "pitta": "pacifying", "kapha": "neutral"}, "rasa": ["sweet", "astringent"], "virya": "cooling"},
    "spinach": {"dosha_effects": {"vata": "neutral", "pitta": "pacifying", "kapha": "pacifying"}, "rasa": ["bitter", "astringent"], "virya": "cooling", "agni_effect": "improving"},
    "rice": {"dosha_effects": {"vata": "pacifying", "pitta": "neutral", "kapha": "neutral_to_aggravating"}, "rasa": ["sweet"], "virya": "cooling", "digestive_load": "moderate"},
    "wheat": {"dosha_effects": {"vata": "pacifying", "pitta": "neutral", "kapha": "neutral_to_aggravating"}, "rasa": ["sweet"], "virya": "heating", "digestive_load": "moderate"},
    "potato": {"dosha_effects": {"vata": "pacifying", "pitta": "neutral", "kapha": "aggravating"}, "rasa": ["sweet"], "virya": "heating", "digestive_load": "moderate"},
    "ginger": {"dosha_effects": {"vata": "pacifying", "pitta": "aggravating", "kapha": "pacifying"}, "rasa": ["pungent"], "virya": "heating", "agni_effect": "improving"},
    "turmeric": {"dosha_effects": {"vata": "pacifying", "pitta": "pacifying", "kapha": "pacifying"}, "rasa": ["bitter", "pungent"], "virya": "heating", "agni_effect": "improving"},
    "milk": {"dosha_effects": {"vata": "pacifying", "pitta": "neutral", "kapha": "aggravating"}, "rasa": ["sweet"], "virya": "cooling", "digestive_load": "moderate"},
    "curd": {"dosha_effects": {"vata": "neutral", "pitta": "aggravating", "kapha": "aggravating"}, "rasa": ["sour"], "virya": "heating", "digestive_load": "moderate"},
    "yogurt": {"dosha_effects": {"vata": "neutral", "pitta": "aggravating", "kapha": "aggravating"}, "rasa": ["sour"], "virya": "heating"},
    "ghee": {"dosha_effects": {"vata": "pacifying", "pitta": "pacifying", "kapha": "neutral"}, "rasa": ["sweet"], "virya": "cooling", "digestive_load": "light", "agni_effect": "improving"},
    "oil": {"dosha_effects": {"vata": "pacifying", "pitta": "neutral_to_aggravating", "kapha": "aggravating"}, "rasa": ["sweet"], "virya": "heating", "digestive_load": "heavy"},
    "banana": {"dosha_effects": {"vata": "pacifying", "pitta": "neutral", "kapha": "aggravating"}, "rasa": ["sweet"], "virya": "cooling", "digestive_load": "moderate"},
    "apple": {"dosha_effects": {"vata": "pacifying", "pitta": "pacifying", "kapha": "neutral"}, "rasa": ["sweet", "astringent"], "virya": "cooling", "digestive_load": "light"},
    "mango": {"dosha_effects": {"vata": "pacifying", "pitta": "aggravating", "kapha": "aggravating"}, "rasa": ["sweet"], "virya": "heating", "digestive_load": "moderate"},
    "coconut": {"dosha_effects": {"vata": "pacifying", "pitta": "pacifying", "kapha": "neutral"}, "rasa": ["sweet"], "virya": "cooling", "digestive_load": "moderate"},
    "almond": {"dosha_effects": {"vata": "pacifying", "pitta": "neutral", "kapha": "aggravating"}, "rasa": ["sweet"], "virya": "heating", "digestive_load": "heavy"},
    "peanut": {"dosha_effects": {"vata": "pacifying", "pitta": "aggravating", "kapha": "aggravating"}, "rasa": ["sweet"], "virya": "heating", "digestive_load": "heavy"},
}

# Cooking state refinements
COOKED_KEYWORDS = ["cooked", "boiled", "fried", "roasted", "steamed", "grilled", "baked", "processed", "dried"]
RAW_KEYWORDS = ["raw", "fresh", "uncooked"]


def infer_dosha_effects(
    category: Optional[str],
    food_name: str,
    nutrition: Optional[KBFoodNutritionBase]
) -> Dict[str, str]:
    """Infer dosha effects from category, name, and nutrition."""
    food_lower = food_name.lower() if food_name else ""
    
    # Check for specific food keyword matches first
    for keyword, props in FOOD_KEYWORD_REFINEMENTS.items():
        if keyword in food_lower:
            if "dosha_effects" in props:
                return props["dosha_effects"]
    
    # Use category-based defaults
    if category:
        normalized_category = category.lower().replace(" ", "_")
        return CATEGORY_TO_DOSHA_EFFECTS.get(normalized_category, {
            "vata": "neutral",
            "pitta": "neutral",
            "kapha": "neutral"
        })
    
    # Default neutral
    return {
        "vata": "neutral",
        "pitta": "neutral",
        "kapha": "neutral"
    }


def infer_rasa(
    category: Optional[str],
    food_name: str
) -> List[str]:
    """Infer rasa (taste) from category and name."""
    food_lower = food_name.lower() if food_name else ""
    
    # Check for specific food keyword matches
    for keyword, props in FOOD_KEYWORD_REFINEMENTS.items():
        if keyword in food_lower:
            if "rasa" in props:
                return props["rasa"]
    
    # Use category-based defaults
    if category:
        normalized_category = category.lower().replace(" ", "_")
        return CATEGORY_TO_RASA.get(normalized_category, ["sweet"])
    
    return ["sweet"]


def infer_virya(
    category: Optional[str],
    food_name: str,
    nutrition: Optional[KBFoodNutritionBase]
) -> str:
    """Infer virya (heating/cooling) from category, name, and nutrition."""
    food_lower = food_name.lower() if food_name else ""
    
    # Check for specific food keyword matches
    for keyword, props in FOOD_KEYWORD_REFINEMENTS.items():
        if keyword in food_lower:
            if "virya" in props:
                return props["virya"]
    
    # Use nutrition data to refine
    if nutrition and nutrition.macros:
        fat_g = safe_float(nutrition.macros.get("fat_g", 0))
        if fat_g > 20:  # High fat foods are generally heating
            return "heating"
    
    # Use category-based defaults
    if category:
        normalized_category = category.lower().replace(" ", "_")
        return CATEGORY_TO_VIRYA.get(normalized_category, "neutral")
    
    return "neutral"


def infer_vipaka(
    category: Optional[str],
    food_name: str
) -> str:
    """Infer vipaka (post-digestive effect) from category and name."""
    food_lower = food_name.lower() if food_name else ""
    
    # Check for specific food keyword matches
    for keyword, props in FOOD_KEYWORD_REFINEMENTS.items():
        if keyword in food_lower:
            if "vipaka" in props:
                return props["vipaka"]
    
    # Use category-based defaults
    if category:
        normalized_category = category.lower().replace(" ", "_")
        return CATEGORY_TO_VIPAKA.get(normalized_category, "sweet")
    
    return "sweet"


def infer_guna(
    category: Optional[str],
    food_name: str
) -> str:
    """Infer guna (quality) from category and name."""
    food_lower = food_name.lower() if food_name else ""
    
    # Check for meat/fish keywords
    if any(term in food_lower for term in ["meat", "chicken", "fish", "egg", "poultry"]):
        if "chicken" in food_lower or "poultry" in food_lower:
            return "rajasic"
        return "tamasic"
    
    # Use category-based defaults
    if category:
        normalized_category = category.lower().replace(" ", "_")
        return CATEGORY_TO_GUNA.get(normalized_category, "sattvic")
    
    return "sattvic"


def infer_digestive_load(
    category: Optional[str],
    food_name: str,
    nutrition: Optional[KBFoodNutritionBase]
) -> str:
    """Infer digestive load from category, name, and nutrition."""
    food_lower = food_name.lower() if food_name else ""
    
    # Check for specific food keyword matches
    for keyword, props in FOOD_KEYWORD_REFINEMENTS.items():
        if keyword in food_lower:
            if "digestive_load" in props:
                return props["digestive_load"]
    
    # Use nutrition data to refine
    if nutrition:
        if nutrition.macros:
            fat_g = safe_float(nutrition.macros.get("fat_g", 0))
            protein_g = safe_float(nutrition.macros.get("protein_g", 0))
            fiber_g = safe_float(nutrition.macros.get("fiber_g", 0))
            
            if fat_g > 20:  # High fat = heavy
                return "heavy"
            if fiber_g > 5 and protein_g < 10:  # High fiber, low protein = light
                return "light"
            if protein_g > 20:  # High protein = moderate to heavy
                return "moderate"
    
    # Use category-based defaults
    if category:
        normalized_category = category.lower().replace(" ", "_")
        return CATEGORY_TO_DIGESTIVE_LOAD.get(normalized_category, "moderate")
    
    return "moderate"


def infer_agni_effect(
    category: Optional[str],
    food_name: str
) -> str:
    """Infer agni effect from category and name."""
    food_lower = food_name.lower() if food_name else ""
    
    # Check for specific food keyword matches
    for keyword, props in FOOD_KEYWORD_REFINEMENTS.items():
        if keyword in food_lower:
            if "agni_effect" in props:
                return props["agni_effect"]
    
    # Check for spices (generally improve agni)
    if any(term in food_lower for term in ["ginger", "turmeric", "cumin", "pepper", "spice"]):
        return "improving"
    
    # Use category-based defaults
    if category:
        normalized_category = category.lower().replace(" ", "_")
        return CATEGORY_TO_AGNI_EFFECT.get(normalized_category, "neutral")
    
    return "neutral"


def infer_food_temperature_preference(
    food_name: str,
    virya: str
) -> str:
    """Infer food temperature preference from virya and cooking state."""
    food_lower = food_name.lower() if food_name else ""
    
    # Check cooking state
    is_cooked = any(keyword in food_lower for keyword in COOKED_KEYWORDS)
    is_raw = any(keyword in food_lower for keyword in RAW_KEYWORDS)
    
    if is_cooked:
        if virya == "cooling":
            return "warm"  # Cooling foods should be eaten warm
        return "warm"
    
    if is_raw:
        return "room"  # Raw foods at room temperature
    
    # Default based on virya
    if virya == "cooling":
        return "cool"
    elif virya == "heating":
        return "warm"
    
    return "warm"


def infer_cooking_method_preference(
    category: Optional[str],
    food_name: str,
    digestive_load: str
) -> List[str]:
    """Infer cooking method preferences."""
    food_lower = food_name.lower() if food_name else ""
    
    # Heavy foods benefit from easier cooking methods
    if digestive_load == "heavy":
        return ["boiled", "steamed"]
    
    # Light foods can handle various methods
    if digestive_load == "light":
        return ["steamed", "boiled", "sautéed"]
    
    # Default moderate
    return ["boiled", "steamed", "roasted"]


def infer_meal_timing_preference(
    category: Optional[str],
    digestive_load: str
) -> List[str]:
    """Infer meal timing preferences."""
    # Heavy foods better for lunch
    if digestive_load == "heavy":
        return ["lunch"]
    
    # Light foods can be eaten anytime
    if digestive_load == "light":
        return ["breakfast", "lunch", "dinner"]
    
    # Moderate foods for lunch and dinner
    return ["lunch", "dinner"]


def infer_season_preference(
    virya: str
) -> List[str]:
    """Infer season preference based on virya."""
    if virya == "cooling":
        return ["summer", "monsoon"]
    elif virya == "heating":
        return ["winter"]
    
    return ["all_seasons"]


def calculate_ayurvedic_profile(
    food: KBFoodMaster,
    nutrition: Optional[KBFoodNutritionBase]
) -> Dict[str, Any]:
    """Calculate complete Ayurvedic profile for a food."""
    dosha_effects = infer_dosha_effects(food.category, food.display_name, nutrition)
    rasa = infer_rasa(food.category, food.display_name)
    virya = infer_virya(food.category, food.display_name, nutrition)
    vipaka = infer_vipaka(food.category, food.display_name)
    guna = infer_guna(food.category, food.display_name)
    digestive_load = infer_digestive_load(food.category, food.display_name, nutrition)
    agni_effect = infer_agni_effect(food.category, food.display_name)
    
    food_temperature_preference = infer_food_temperature_preference(food.display_name, virya)
    cooking_method_preference = infer_cooking_method_preference(food.category, food.display_name, digestive_load)
    meal_timing_preference = infer_meal_timing_preference(food.category, digestive_load)
    season_preference = infer_season_preference(virya)
    
    return {
        "dosha_effects": dosha_effects,
        "guna": guna,
        "rasa": rasa,
        "virya": virya,
        "vipaka": vipaka,
        "agni_effect": agni_effect,
        "digestive_load": digestive_load,
        "food_temperature_preference": food_temperature_preference,
        "cooking_method_preference": cooking_method_preference,
        "meal_timing_preference": meal_timing_preference,
        "season_preference": season_preference,
    }


def import_ayurvedic_profiles(
    db: Session,
    batch_size: int = 50,
    dry_run: bool = False
) -> Dict[str, int]:
    """Import Ayurvedic profiles for all foods."""
    stats = {
        "total_foods": 0,
        "processed": 0,
        "created": 0,
        "updated": 0,
        "errors": 0,
    }
    
    # Get all foods
    foods = db.query(KBFoodMaster).all()
    stats["total_foods"] = len(foods)
    
    logger.info(f"Processing {len(foods)} foods...")
    
    for idx, food in enumerate(foods):
        try:
            nutrition = food.nutrition
            
            # Calculate Ayurvedic profile
            profile_data = calculate_ayurvedic_profile(food, nutrition)
            
            # Check if profile exists
            existing_profile = db.query(KBFoodAyurvedicProfile).filter(
                KBFoodAyurvedicProfile.food_id == food.food_id
            ).first()
            
            if existing_profile:
                # Update existing
                existing_profile.dosha_effects = profile_data["dosha_effects"]
                existing_profile.guna = profile_data["guna"]
                existing_profile.rasa = profile_data["rasa"]
                existing_profile.virya = profile_data["virya"]
                existing_profile.vipaka = profile_data["vipaka"]
                existing_profile.agni_effect = profile_data["agni_effect"]
                existing_profile.digestive_load = profile_data["digestive_load"]
                existing_profile.food_temperature_preference = profile_data["food_temperature_preference"]
                existing_profile.cooking_method_preference = profile_data["cooking_method_preference"]
                existing_profile.meal_timing_preference = profile_data["meal_timing_preference"]
                existing_profile.season_preference = profile_data["season_preference"]
                
                if not dry_run:
                    db.add(existing_profile)
                
                stats["updated"] += 1
            else:
                # Create new
                new_profile = KBFoodAyurvedicProfile(
                    food_id=food.food_id,
                    dosha_effects=profile_data["dosha_effects"],
                    guna=profile_data["guna"],
                    rasa=profile_data["rasa"],
                    virya=profile_data["virya"],
                    vipaka=profile_data["vipaka"],
                    agni_effect=profile_data["agni_effect"],
                    digestive_load=profile_data["digestive_load"],
                    food_temperature_preference=profile_data["food_temperature_preference"],
                    cooking_method_preference=profile_data["cooking_method_preference"],
                    meal_timing_preference=profile_data["meal_timing_preference"],
                    season_preference=profile_data["season_preference"],
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
    parser = argparse.ArgumentParser(description="Import Ayurvedic profiles to food KB")
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size for commits")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    
    args = parser.parse_args()
    
    db = SessionLocal()
    
    try:
        stats = import_ayurvedic_profiles(db, args.batch_size, args.dry_run)
        
        logger.info("=" * 70)
        logger.info("SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Total foods: {stats['total_foods']}")
        logger.info(f"Processed: {stats['processed']}")
        logger.info(f"Created: {stats['created']}")
        logger.info(f"Updated: {stats['updated']}")
        logger.info(f"Errors: {stats['errors']}")
        logger.info("=" * 70)
        logger.info("Note: This is rule-based inference (~60-70% accuracy).")
        logger.info("Can be refined later with LLM for food-specific accuracy.")
        logger.info("=" * 70)
        
    finally:
        db.close()


if __name__ == "__main__":
    main()

