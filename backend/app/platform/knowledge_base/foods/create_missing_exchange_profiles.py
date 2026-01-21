"""
Create missing exchange profiles for foods that should have them.

This script:
1. Finds foods that map to IET exchange categories
2. Have nutrition data but are missing exchange profiles
3. Creates exchange profiles for them (calculating calories from macros if needed)
"""

import sys
from pathlib import Path

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
from app.platform.knowledge_base.foods.enrich_food_master_metadata import (
    map_to_iet_exchange_category,
    EXCHANGE_STANDARDS,
)


def create_missing_exchange_profiles(dry_run: bool = False):
    """Create exchange profiles for foods that should have them but don't."""
    
    db = SessionLocal()
    
    try:
        # Get all foods
        all_foods = db.query(KBFoodMaster).all()
        
        # Get existing exchange profiles
        existing_profiles = db.query(KBFoodExchangeProfile).all()
        existing_food_ids = {p.food_id for p in existing_profiles}
        
        stats = {
            "checked": 0,
            "created": 0,
            "updated_calories": 0,
            "skipped_no_iet": 0,
            "skipped_no_nutrition": 0,
            "skipped_no_macros": 0,
        }
        
        logger.info("=" * 70)
        logger.info("CREATING MISSING EXCHANGE PROFILES")
        logger.info("=" * 70)
        logger.info(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
        logger.info("")
        
        for food in all_foods:
            stats["checked"] += 1
            
            # Skip if already has exchange profile
            if food.food_id in existing_food_ids:
                continue
            
            # Check if maps to IET category
            iet_category = map_to_iet_exchange_category(
                food.category or "", 
                food.display_name or ""
            )
            
            if not iet_category:
                stats["skipped_no_iet"] += 1
                continue
            
            # Get nutrition data
            nutrition = db.query(KBFoodNutritionBase).filter(
                KBFoodNutritionBase.food_id == food.food_id
            ).first()
            
            if not nutrition:
                stats["skipped_no_nutrition"] += 1
                continue
            
            # Get or calculate calories
            calories_per_100g = float(nutrition.calories_kcal) if nutrition.calories_kcal else None
            
            # If calories missing, calculate from macros
            if not calories_per_100g or calories_per_100g <= 0:
                if nutrition.macros:
                    macros = nutrition.macros
                    protein_g = float(macros.get('protein_g', 0) or 0)
                    carbs_g = float(macros.get('carbs_g', 0) or 0)
                    fat_g = float(macros.get('fat_g', 0) or 0)
                    
                    if protein_g > 0 or carbs_g > 0 or fat_g > 0:
                        calculated_calories = (protein_g * 4) + (carbs_g * 4) + (fat_g * 9)
                        if calculated_calories > 0:
                            calories_per_100g = calculated_calories
                            if not dry_run:
                                nutrition.calories_kcal = calculated_calories
                                db.add(nutrition)
                            stats["updated_calories"] += 1
                            logger.debug(f"Calculated calories for {food.food_id}: {calories_per_100g:.2f} kcal")
                else:
                    stats["skipped_no_macros"] += 1
                    continue
            
            if not calories_per_100g or calories_per_100g <= 0:
                continue
            
            # Get exchange standard
            standard = EXCHANGE_STANDARDS.get(iet_category)
            if not standard:
                continue
            
            # Calculate serving size per exchange
            serving_size_per_exchange_g = (standard["calories"] / calories_per_100g) * 100
            
            # Get common serving size
            common_serving_size_g = float(food.common_serving_size_g) if food.common_serving_size_g else None
            exchanges_per_common_serving = None
            if common_serving_size_g and common_serving_size_g > 0:
                exchanges_per_common_serving = common_serving_size_g / serving_size_per_exchange_g
            
            # Create notes
            notes = f"1 exchange = {round(serving_size_per_exchange_g, 1)}g ≈ {standard['calories']} kcal"
            
            # Create exchange profile
            if dry_run:
                logger.info(f"  [DRY RUN] Would create exchange profile: {food.food_id} - {food.display_name} ({iet_category})")
            else:
                exchange_profile = KBFoodExchangeProfile(
                    food_id=food.food_id,
                    exchange_category=iet_category,
                    serving_size_per_exchange_g=round(serving_size_per_exchange_g, 2),
                    exchanges_per_common_serving=round(exchanges_per_common_serving, 2) if exchanges_per_common_serving else None,
                    notes=notes
                )
                db.add(exchange_profile)
            
            stats["created"] += 1
            
            # Commit in batches
            if not dry_run and stats["created"] % 50 == 0:
                db.commit()
                logger.info(f"  Committed {stats['created']} exchange profiles...")
        
        # Final commit
        if not dry_run:
            db.commit()
        
        logger.info("")
        logger.info("=" * 70)
        logger.info("SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Foods checked: {stats['checked']}")
        logger.info(f"Exchange profiles created: {stats['created']}")
        logger.info(f"Calories calculated from macros: {stats['updated_calories']}")
        logger.info(f"Skipped (no IET category): {stats['skipped_no_iet']}")
        logger.info(f"Skipped (no nutrition data): {stats['skipped_no_nutrition']}")
        logger.info(f"Skipped (no macros): {stats['skipped_no_macros']}")
        logger.info("=" * 70)
        
        return stats
    
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Create missing exchange profiles')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    args = parser.parse_args()
    
    create_missing_exchange_profiles(dry_run=args.dry_run)

