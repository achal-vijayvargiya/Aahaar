"""
Diagnostic script to analyze why exchange profiles weren't created for all foods.

Checks:
1. Which foods don't have exchange profiles
2. Why they don't have profiles (no IET mapping, no nutrition data, no calories)
3. Breakdown by category
"""

import sys
from pathlib import Path
from collections import defaultdict

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

# Import mapping from enrich script
sys.path.insert(0, str(Path(__file__).parent))
from app.platform.knowledge_base.foods.enrich_food_master_metadata import (
    CSV_EXCHANGE_TO_IET_CATEGORY,
    map_to_iet_exchange_category,
    normalize_category
)


def diagnose_exchange_profiles():
    """Diagnose why exchange profiles are missing."""
    
    db = SessionLocal()
    
    try:
        # Get all foods
        all_foods = db.query(KBFoodMaster).all()
        total_foods = len(all_foods)
        
        # Get foods with exchange profiles
        foods_with_profiles = db.query(KBFoodExchangeProfile).all()
        profile_food_ids = {p.food_id for p in foods_with_profiles}
        
        # Statistics
        stats = {
            "total_foods": total_foods,
            "with_exchange_profiles": len(profile_food_ids),
            "without_exchange_profiles": 0,
            "no_iet_category": 0,
            "no_nutrition_data": 0,
            "no_calories": 0,
            "categories": defaultdict(lambda: {"total": 0, "with_profile": 0, "no_iet": 0, "no_nutrition": 0, "no_calories": 0}),
            "samples": {
                "no_iet_category": [],
                "no_nutrition_data": [],
                "no_calories": [],
            }
        }
        
        logger.info("=" * 70)
        logger.info("EXCHANGE PROFILE DIAGNOSIS")
        logger.info("=" * 70)
        logger.info(f"Total foods in kb_food_master: {total_foods}")
        logger.info(f"Foods with exchange profiles: {len(profile_food_ids)}")
        logger.info("")
        
        # Analyze each food without a profile
        for food in all_foods:
            category = food.category or "uncategorized"
            stats["categories"][category]["total"] += 1
            
            if food.food_id in profile_food_ids:
                stats["categories"][category]["with_profile"] += 1
                continue
            
            # Food doesn't have exchange profile - find out why
            stats["without_exchange_profiles"] += 1
            
            # Check if it maps to IET category
            # Try to get exchange category from CSV mapping
            if category:
                iet_category = map_to_iet_exchange_category(category, food.display_name or "")
            else:
                iet_category = None
            
            if not iet_category:
                stats["no_iet_category"] += 1
                stats["categories"][category]["no_iet"] += 1
                if len(stats["samples"]["no_iet_category"]) < 10:
                    stats["samples"]["no_iet_category"].append({
                        "food_id": food.food_id,
                        "display_name": food.display_name,
                        "category": category
                    })
                continue
            
            # Check nutrition data
            nutrition = db.query(KBFoodNutritionBase).filter(
                KBFoodNutritionBase.food_id == food.food_id
            ).first()
            
            if not nutrition:
                stats["no_nutrition_data"] += 1
                stats["categories"][category]["no_nutrition"] += 1
                if len(stats["samples"]["no_nutrition_data"]) < 10:
                    stats["samples"]["no_nutrition_data"].append({
                        "food_id": food.food_id,
                        "display_name": food.display_name,
                        "category": category,
                        "iet_category": iet_category
                    })
                continue
            
            # Check calories
            calories = float(nutrition.calories_kcal) if nutrition.calories_kcal else None
            if not calories or calories <= 0:
                stats["no_calories"] += 1
                stats["categories"][category]["no_calories"] += 1
                if len(stats["samples"]["no_calories"]) < 10:
                    stats["samples"]["no_calories"].append({
                        "food_id": food.food_id,
                        "display_name": food.display_name,
                        "category": category,
                        "iet_category": iet_category,
                        "calories": calories
                    })
                continue
            
            # Should have profile but doesn't - this is unexpected
            logger.warning(f"Food {food.food_id} should have exchange profile but doesn't: {food.display_name}")
        
        # Print summary
        logger.info("")
        logger.info("=" * 70)
        logger.info("BREAKDOWN BY REASON")
        logger.info("=" * 70)
        logger.info(f"Foods without exchange profiles: {stats['without_exchange_profiles']}")
        logger.info(f"  - No IET category mapping: {stats['no_iet_category']}")
        logger.info(f"  - No nutrition data: {stats['no_nutrition_data']}")
        logger.info(f"  - No calories in nutrition data: {stats['no_calories']}")
        logger.info("")
        
        # Print category breakdown
        logger.info("=" * 70)
        logger.info("BREAKDOWN BY CATEGORY")
        logger.info("=" * 70)
        for category in sorted(stats["categories"].keys()):
            cat_stats = stats["categories"][category]
            logger.info(f"\n{category}:")
            logger.info(f"  Total: {cat_stats['total']}")
            logger.info(f"  With exchange profile: {cat_stats['with_profile']}")
            logger.info(f"  Without profile:")
            logger.info(f"    - No IET mapping: {cat_stats['no_iet']}")
            logger.info(f"    - No nutrition data: {cat_stats['no_nutrition']}")
            logger.info(f"    - No calories: {cat_stats['no_calories']}")
        
        # Print samples
        logger.info("")
        logger.info("=" * 70)
        logger.info("SAMPLE FOODS WITHOUT IET CATEGORY (expected - don't fit exchange system)")
        logger.info("=" * 70)
        for sample in stats["samples"]["no_iet_category"][:10]:
            logger.info(f"  - {sample['food_id']}: {sample['display_name']} (category: {sample['category']})")
        
        logger.info("")
        logger.info("=" * 70)
        logger.info("SAMPLE FOODS WITHOUT NUTRITION DATA (need nutrition import)")
        logger.info("=" * 70)
        for sample in stats["samples"]["no_nutrition_data"][:10]:
            logger.info(f"  - {sample['food_id']}: {sample['display_name']} (category: {sample['category']}, IET: {sample['iet_category']})")
        
        logger.info("")
        logger.info("=" * 70)
        logger.info("SAMPLE FOODS WITHOUT CALORIES (need nutrition data fix)")
        logger.info("=" * 70)
        for sample in stats["samples"]["no_calories"][:10]:
            logger.info(f"  - {sample['food_id']}: {sample['display_name']} (category: {sample['category']}, IET: {sample['iet_category']}, calories: {sample['calories']})")
        
        logger.info("")
        logger.info("=" * 70)
        
        return stats
    
    finally:
        db.close()


if __name__ == "__main__":
    diagnose_exchange_profiles()

