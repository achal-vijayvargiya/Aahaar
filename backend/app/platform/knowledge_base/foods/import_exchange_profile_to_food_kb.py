"""
Import Exchange Profile data to kb_food_exchange_profile table.

This script creates exchange profiles for all foods that fit the IET exchange system.
Calculates serving_size_per_exchange_g from nutrition data.

Note: exchanges_per_common_serving will be NULL if common_serving_size_g is not available.
This can be updated later when common_serving_size_g is populated.

Usage:
    python -m app.platform.knowledge_base.foods.import_exchange_profile_to_food_kb
    python -m app.platform.knowledge_base.foods.import_exchange_profile_to_food_kb --dry-run
    python -m app.platform.knowledge_base.foods.import_exchange_profile_to_food_kb --batch-size 50
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
from app.platform.data.models.kb_food_exchange_profile import KBFoodExchangeProfile
from app.utils.logger import logger


# Mapping from CSV exchange column values to IET exchange categories
CSV_EXCHANGE_TO_IET_CATEGORY = {
    # IET exchange categories
    "cereals_and_millets": "cereal",
    "cereals and millets": "cereal",
    "grain_legumes": "pulse",
    "grain legumes": "pulse",
    "fruits": "fruit",
    "green_leafy_vegetables": "vegetable_non_starchy",
    "green leafy vegetables": "vegetable_non_starchy",
    "other_vegetables": "vegetable_non_starchy",  # Default, will refine based on food name
    "other vegetables": "vegetable_non_starchy",
    "roots_and_tubers": "vegetable_starchy",
    "roots and tubers": "vegetable_starchy",
    "nuts_and_oil_seeds": "nuts_seeds",
    "nuts and oil seeds": "nuts_seeds",
    "mushrooms": "vegetable_non_starchy",
    # Foods that don't fit IET exchange system (return None)
    "animal_meat": None,
    "animal meat": None,
    "poultry": None,
    "marine_fish": None,
    "marine fish": None,
    "condiments_and_spices": None,
    "condiments and spices": None,
    "miscellaneous_foods": None,
    "miscellaneous foods": None,
    "egg_and_egg_products": None,
    "egg and egg products": None,
    "sugars": None,
}

# Starchy vegetables keywords (to refine vegetable_non_starchy)
STARCHY_VEGETABLES = ["potato", "sweet potato", "yam", "taro", "arbi", "colocasia"]


def load_exchange_category_definitions() -> Dict[str, Dict[str, float]]:
    """Load exchange category definitions from JSON file."""
    definitions_path = Path(__file__).parent.parent / "exchange_system" / "exchange_category_definitions_kb.json"
    with open(definitions_path, 'r', encoding='utf-8') as f:
        categories = json.load(f)
    
    # Convert to dictionary with exchange_category_id as key
    standards = {}
    for category in categories:
        if category.get("status") == "active":
            cat_id = category.get("exchange_category_id")
            nutrition = category.get("nutrition_per_exchange", {})
            standards[cat_id] = {
                "calories": float(nutrition.get("calories", 0)),
                "protein": float(nutrition.get("protein_g", 0)),
                "carbs": float(nutrition.get("carbs_g", 0)),
                "fat": float(nutrition.get("fat_g", 0)),
            }
    
    return standards


def map_to_iet_exchange_category(category: Optional[str], food_name: str = "") -> Optional[str]:
    """
    Map food category to IET exchange category.
    
    Returns one of the 8 IET exchange categories, or None if food doesn't fit exchange system.
    
    Args:
        category: Food category from kb_food_master (e.g., "cereals_and_millets")
        food_name: Food name for refinement (e.g., to distinguish starchy vs non-starchy vegetables)
    
    Returns:
        IET exchange category or None
    """
    if not category:
        # Try to infer from food name
        food_lower = food_name.lower() if food_name else ""
        
        # Check for starchy vegetables
        if any(veg in food_lower for veg in STARCHY_VEGETABLES):
            return "vegetable_starchy"
        
        # Check for common patterns
        if any(term in food_lower for term in ["rice", "wheat", "oats", "millet", "bajra", "jowar", "ragi", "roti", "bread"]):
            return "cereal"
        if any(term in food_lower for term in ["dal", "lentil", "chana", "rajma", "moong", "masoor", "toor"]):
            return "pulse"
        if any(term in food_lower for term in ["milk", "curd", "yogurt", "buttermilk", "paneer", "cheese"]):
            return "milk"
        if any(term in food_lower for term in ["apple", "banana", "orange", "papaya", "mango", "guava"]):
            return "fruit"
        if any(term in food_lower for term in ["almond", "peanut", "walnut", "cashew", "seed"]):
            return "nuts_seeds"
        if any(term in food_lower for term in ["oil", "ghee", "butter"]):
            return "fat"
        
        return None
    
    # Normalize: lowercase, replace spaces with underscores
    normalized = category.strip().lower().replace(" ", "_")
    
    # Get IET category
    iet_category = CSV_EXCHANGE_TO_IET_CATEGORY.get(normalized)
    
    # Refine vegetable category based on food name
    if iet_category == "vegetable_non_starchy":
        food_lower = food_name.lower() if food_name else ""
        if any(veg in food_lower for veg in STARCHY_VEGETABLES):
            return "vegetable_starchy"
    
    return iet_category


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


def calculate_serving_size_per_exchange(
    calories_per_100g: float,
    standard_calories: float
) -> float:
    """
    Calculate serving size per exchange in grams.
    
    Formula: serving_size_per_exchange_g = (standard_calories / calories_per_100g) * 100
    """
    if calories_per_100g <= 0:
        return 0.0
    
    return (standard_calories / calories_per_100g) * 100


def import_exchange_profiles(
    db: Session,
    batch_size: int = 50,
    dry_run: bool = False
) -> Dict[str, int]:
    """Import exchange profiles for all foods."""
    stats = {
        "total_foods": 0,
        "processed": 0,
        "created": 0,
        "updated": 0,
        "skipped_no_iet_category": 0,
        "skipped_no_nutrition": 0,
        "skipped_no_calories": 0,
        "calories_calculated": 0,
        "errors": 0,
    }
    
    # Load exchange category definitions
    logger.info("Loading exchange category definitions...")
    exchange_standards = load_exchange_category_definitions()
    logger.info(f"Loaded {len(exchange_standards)} exchange categories")
    
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
            
            # Map to IET exchange category
            iet_category = map_to_iet_exchange_category(food.category, food.display_name)
            
            if not iet_category:
                stats["skipped_no_iet_category"] += 1
                continue
            
            # Get exchange standard
            standard = exchange_standards.get(iet_category)
            if not standard:
                stats["skipped_no_iet_category"] += 1
                continue
            
            # Get or calculate calories
            calories_per_100g = safe_float(nutrition.calories_kcal)
            
            # If calories missing, calculate from macros
            if calories_per_100g <= 0:
                if nutrition.macros:
                    macros = nutrition.macros
                    protein_g = safe_float(macros.get('protein_g', 0))
                    carbs_g = safe_float(macros.get('carbs_g', 0))
                    fat_g = safe_float(macros.get('fat_g', 0))
                    
                    if protein_g > 0 or carbs_g > 0 or fat_g > 0:
                        calculated_calories = (protein_g * 4) + (carbs_g * 4) + (fat_g * 9)
                        if calculated_calories > 0:
                            calories_per_100g = calculated_calories
                            if not dry_run:
                                nutrition.calories_kcal = Decimal(str(calculated_calories))
                                db.add(nutrition)
                            stats["calories_calculated"] += 1
                            logger.debug(f"Calculated calories for {food.food_id}: {calories_per_100g:.2f} kcal")
                else:
                    stats["skipped_no_calories"] += 1
                    continue
            
            if calories_per_100g <= 0:
                stats["skipped_no_calories"] += 1
                continue
            
            # Calculate serving size per exchange
            serving_size_per_exchange_g = calculate_serving_size_per_exchange(
                calories_per_100g,
                standard["calories"]
            )
            
            if serving_size_per_exchange_g <= 0:
                stats["skipped_no_calories"] += 1
                continue
            
            # Calculate exchanges per common serving (if available)
            exchanges_per_common_serving = None
            if food.common_serving_size_g:
                common_serving_size_g = safe_float(food.common_serving_size_g)
                if common_serving_size_g > 0:
                    exchanges_per_common_serving = common_serving_size_g / serving_size_per_exchange_g
            
            # Create notes
            notes = f"1 exchange = {round(serving_size_per_exchange_g, 1)}g ≈ {standard['calories']} kcal"
            
            # Check if exchange profile exists
            existing_profile = db.query(KBFoodExchangeProfile).filter(
                KBFoodExchangeProfile.food_id == food.food_id
            ).first()
            
            if existing_profile:
                # Update existing
                updated = False
                if existing_profile.exchange_category != iet_category:
                    existing_profile.exchange_category = iet_category
                    updated = True
                if abs(float(existing_profile.serving_size_per_exchange_g or 0) - serving_size_per_exchange_g) > 0.01:
                    existing_profile.serving_size_per_exchange_g = round(serving_size_per_exchange_g, 2)
                    updated = True
                if exchanges_per_common_serving:
                    if abs(float(existing_profile.exchanges_per_common_serving or 0) - exchanges_per_common_serving) > 0.01:
                        existing_profile.exchanges_per_common_serving = round(exchanges_per_common_serving, 2)
                        updated = True
                if existing_profile.notes != notes:
                    existing_profile.notes = notes
                    updated = True
                
                if updated and not dry_run:
                    db.add(existing_profile)
                
                stats["updated"] += 1
            else:
                # Create new
                new_profile = KBFoodExchangeProfile(
                    food_id=food.food_id,
                    exchange_category=iet_category,
                    serving_size_per_exchange_g=round(serving_size_per_exchange_g, 2),
                    exchanges_per_common_serving=round(exchanges_per_common_serving, 2) if exchanges_per_common_serving else None,
                    notes=notes
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
    parser = argparse.ArgumentParser(description="Import exchange profiles to food KB")
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size for commits")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    
    args = parser.parse_args()
    
    db = SessionLocal()
    
    try:
        stats = import_exchange_profiles(db, args.batch_size, args.dry_run)
        
        logger.info("=" * 70)
        logger.info("SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Total foods: {stats['total_foods']}")
        logger.info(f"Processed: {stats['processed']}")
        logger.info(f"Created: {stats['created']}")
        logger.info(f"Updated: {stats['updated']}")
        logger.info(f"Calories calculated from macros: {stats['calories_calculated']}")
        logger.info(f"Skipped (no IET category): {stats['skipped_no_iet_category']}")
        logger.info(f"Skipped (no nutrition): {stats['skipped_no_nutrition']}")
        logger.info(f"Skipped (no calories): {stats['skipped_no_calories']}")
        logger.info(f"Errors: {stats['errors']}")
        logger.info("=" * 70)
        logger.info("Note: exchanges_per_common_serving will be NULL if common_serving_size_g is not available.")
        logger.info("This can be updated later when common_serving_size_g is populated.")
        logger.info("=" * 70)
        
    finally:
        db.close()


if __name__ == "__main__":
    main()

