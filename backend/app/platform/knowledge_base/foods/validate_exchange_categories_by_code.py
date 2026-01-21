"""
Validate and correct exchange category mappings based on code prefixes.

This script validates exchange_category in kb_food_exchange_profile against
the code prefix (first character) in kb_food_master.food_id.

Code Prefix Mapping:
- A → cereal
- B → pulse
- C,D → vegetable_non_starchy
- F → vegetable_starchy
- E → fruit
- L → milk or paneer (distinguished by food name)
- M → egg_whites
- H → nuts_seeds
- T → fat
- I → jaggery
- J → unknown (skipped for now)

Usage:
    python -m app.platform.knowledge_base.foods.validate_exchange_categories_by_code
    python -m app.platform.knowledge_base.foods.validate_exchange_categories_by_code --dry-run
    python -m app.platform.knowledge_base.foods.validate_exchange_categories_by_code --fix
"""

import sys
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from collections import defaultdict

# Add backend directory to path
backend_dir = Path(__file__).parent.parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database import SessionLocal
from app.platform.data.models.kb_food_master import KBFoodMaster
from app.platform.data.models.kb_food_exchange_profile import KBFoodExchangeProfile
from app.utils.logger import logger


# Code prefix to exchange category mapping
# Note: J prefix is intentionally excluded (unknown category, skipped for now)
CODE_PREFIX_TO_EXCHANGE: Dict[str, List[str]] = {
    "A": ["cereal"],
    "B": ["pulse"],
    "C": ["vegetable_non_starchy"],
    "D": ["vegetable_non_starchy"],
    "E": ["fruit"],
    "F": ["vegetable_starchy"],
    "H": ["nuts_seeds"],
    "I": ["jaggery"],
    "L": ["milk", "paneer"],  # Can be either - need to check food name
    "M": ["egg_whites"],
    "T": ["fat"],
    # J is intentionally not included - unknown category, skipped for now
}

# Keywords to distinguish milk vs paneer for L prefix
MILK_KEYWORDS = ["milk", "curd", "yogurt", "buttermilk", "dahi", "lassi"]
PANEER_KEYWORDS = ["paneer", "cheese", "cottage cheese", "chena"]


def get_expected_exchange_category(food_id: str, food_name: str) -> Optional[str]:
    """
    Get expected exchange category based on code prefix.
    
    Args:
        food_id: Food ID (e.g., "A001", "T001")
        food_name: Food display name (for distinguishing milk vs paneer)
    
    Returns:
        Expected exchange category or None if prefix not recognized
    """
    if not food_id:
        return None
    
    prefix = food_id[0].upper()
    possible_categories = CODE_PREFIX_TO_EXCHANGE.get(prefix)
    
    if not possible_categories:
        return None
    
    # If only one possible category, return it
    if len(possible_categories) == 1:
        return possible_categories[0]
    
    # For L prefix (milk or paneer), check food name
    if prefix == "L":
        food_lower = (food_name or "").lower()
        
        # Check for paneer keywords first (more specific)
        if any(keyword in food_lower for keyword in PANEER_KEYWORDS):
            return "paneer"
        
        # Check for milk keywords
        if any(keyword in food_lower for keyword in MILK_KEYWORDS):
            return "milk"
        
        # Default to milk if unclear
        logger.debug(f"Unclear for L prefix: {food_id} - {food_name}, defaulting to milk")
        return "milk"
    
    # Should not reach here, but return first option as fallback
    return possible_categories[0]


def validate_exchange_categories(
    db: Session,
    dry_run: bool = False,
    fix: bool = False
) -> Dict[str, any]:
    """
    Validate and optionally fix exchange category mappings.
    
    Args:
        db: Database session
        dry_run: If True, only report issues without fixing
        fix: If True, update incorrect mappings (ignored if dry_run is True)
    
    Returns:
        Statistics dictionary
    """
    stats = {
        "total_foods": 0,
        "with_exchange_profile": 0,
        "without_exchange_profile": 0,
        "valid": 0,
        "invalid": 0,
        "fixed": 0,
        "unfixable": 0,  # Code prefix not recognized (including J - unknown)
        "skipped_j_prefix": 0,  # J prefix foods explicitly skipped
        "by_category": defaultdict(lambda: {"valid": 0, "invalid": 0, "fixed": 0}),
        "errors": [],
    }
    
    logger.info("=" * 70)
    logger.info("VALIDATING EXCHANGE CATEGORY MAPPINGS BY CODE PREFIX")
    logger.info("=" * 70)
    logger.info(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    logger.info(f"Fix mode: {'ON' if (fix and not dry_run) else 'OFF'}")
    logger.info("")
    
    # Get all foods with exchange profiles
    foods_with_profiles = db.query(
        KBFoodMaster.food_id,
        KBFoodMaster.display_name,
        KBFoodExchangeProfile.exchange_category
    ).join(
        KBFoodExchangeProfile,
        KBFoodMaster.food_id == KBFoodExchangeProfile.food_id
    ).all()
    
    stats["with_exchange_profile"] = len(foods_with_profiles)
    
    # Get all foods without exchange profiles
    all_food_ids = {f.food_id for f in db.query(KBFoodMaster.food_id).all()}
    profile_food_ids = {f.food_id for f in foods_with_profiles}
    stats["without_exchange_profile"] = len(all_food_ids - profile_food_ids)
    stats["total_foods"] = len(all_food_ids)
    
    logger.info(f"Total foods: {stats['total_foods']}")
    logger.info(f"Foods with exchange profiles: {stats['with_exchange_profile']}")
    logger.info(f"Foods without exchange profiles: {stats['without_exchange_profile']}")
    logger.info("")
    
    # Validate each food
    invalid_foods = []
    
    for food_id, display_name, current_category in foods_with_profiles:
        # Check if J prefix (explicitly skip)
        prefix = food_id[0].upper() if food_id else "?"
        if prefix == "J":
            stats["skipped_j_prefix"] += 1
            stats["unfixable"] += 1
            continue
        
        # Get expected category based on code prefix
        expected_category = get_expected_exchange_category(food_id, display_name)
        
        if expected_category is None:
            # Code prefix not recognized - can't validate
            stats["unfixable"] += 1
            continue
        
        # Check if current category matches expected
        if current_category == expected_category:
            stats["valid"] += 1
            stats["by_category"][current_category]["valid"] += 1
        else:
            # Mismatch found
            stats["invalid"] += 1
            stats["by_category"][current_category]["invalid"] += 1
            
            invalid_foods.append({
                "food_id": food_id,
                "display_name": display_name,
                "current_category": current_category,
                "expected_category": expected_category,
                "code_prefix": food_id[0].upper() if food_id else "?",
            })
            
            # Fix if requested
            if fix and not dry_run:
                try:
                    exchange_profile = db.query(KBFoodExchangeProfile).filter(
                        KBFoodExchangeProfile.food_id == food_id
                    ).first()
                    
                    if exchange_profile:
                        exchange_profile.exchange_category = expected_category
                        db.add(exchange_profile)
                        stats["fixed"] += 1
                        stats["by_category"][expected_category]["fixed"] += 1
                        logger.info(
                            f"  [FIXED] {food_id} ({display_name}): "
                            f"{current_category} → {expected_category}"
                        )
                except Exception as e:
                    logger.error(f"Error fixing {food_id}: {e}")
                    stats["errors"].append({"food_id": food_id, "error": str(e)})
    
    # Commit fixes
    if fix and not dry_run and stats["fixed"] > 0:
        db.commit()
        logger.info(f"\nCommitted {stats['fixed']} corrections")
    
    # Print summary
    logger.info("")
    logger.info("=" * 70)
    logger.info("VALIDATION SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Total foods with exchange profiles: {stats['with_exchange_profile']}")
    logger.info(f"Valid mappings: {stats['valid']}")
    logger.info(f"Invalid mappings: {stats['invalid']}")
    logger.info(f"Fixed: {stats['fixed']}")
    logger.info(f"Unfixable (unknown code prefix): {stats['unfixable']}")
    if stats["skipped_j_prefix"] > 0:
        logger.info(f"Skipped J prefix (unknown category): {stats['skipped_j_prefix']}")
    logger.info("")
    
    # Print breakdown by category
    if stats["by_category"]:
        logger.info("Breakdown by current category:")
        for category in sorted(stats["by_category"].keys()):
            cat_stats = stats["by_category"][category]
            logger.info(
                f"  {category}: {cat_stats['valid']} valid, "
                f"{cat_stats['invalid']} invalid, {cat_stats['fixed']} fixed"
            )
        logger.info("")
    
    # Print sample invalid foods
    if invalid_foods:
        logger.info("=" * 70)
        logger.info("SAMPLE INVALID MAPPINGS")
        logger.info("=" * 70)
        sample_size = min(20, len(invalid_foods))
        for item in invalid_foods[:sample_size]:
            logger.info(
                f"  {item['food_id']} ({item['display_name']}): "
                f"Code prefix '{item['code_prefix']}' → Expected '{item['expected_category']}', "
                f"but found '{item['current_category']}'"
            )
        if len(invalid_foods) > sample_size:
            logger.info(f"  ... and {len(invalid_foods) - sample_size} more")
        logger.info("")
    
    # Print code prefix statistics
    logger.info("=" * 70)
    logger.info("CODE PREFIX STATISTICS")
    logger.info("=" * 70)
    prefix_stats = defaultdict(lambda: {"count": 0, "categories": defaultdict(int)})
    
    for food_id, display_name, category in foods_with_profiles:
        prefix = food_id[0].upper() if food_id else "?"
        prefix_stats[prefix]["count"] += 1
        prefix_stats[prefix]["categories"][category] += 1
    
    for prefix in sorted(prefix_stats.keys()):
        stats_data = prefix_stats[prefix]
        expected = CODE_PREFIX_TO_EXCHANGE.get(prefix, ["unknown"])
        logger.info(f"  Prefix '{prefix}': {stats_data['count']} foods")
        logger.info(f"    Expected: {', '.join(expected)}")
        logger.info(f"    Actual categories:")
        for cat, count in sorted(stats_data["categories"].items()):
            logger.info(f"      {cat}: {count}")
        logger.info("")
    
    return stats


def create_missing_exchange_profiles_by_code(
    db: Session,
    dry_run: bool = False
) -> Dict[str, int]:
    """
    Create exchange profiles for foods that don't have them, based on code prefix.
    
    Note: This only creates the exchange_profile record. Nutrition data and
    serving_size_per_exchange_g should be calculated separately.
    """
    stats = {
        "checked": 0,
        "created": 0,
        "skipped_no_prefix": 0,
        "errors": 0,
    }
    
    logger.info("=" * 70)
    logger.info("CREATING MISSING EXCHANGE PROFILES BY CODE PREFIX")
    logger.info("=" * 70)
    
    # Get all foods
    all_foods = db.query(KBFoodMaster).all()
    
    # Get existing exchange profiles
    existing_profiles = db.query(KBFoodExchangeProfile.food_id).all()
    existing_food_ids = {p[0] for p in existing_profiles}
    
    for food in all_foods:
        stats["checked"] += 1
        
        # Skip if already has exchange profile
        if food.food_id in existing_food_ids:
            continue
        
        # Skip J prefix (unknown category)
        prefix = food.food_id[0].upper() if food.food_id else "?"
        if prefix == "J":
            stats["skipped_no_prefix"] += 1
            continue
        
        # Get expected category based on code prefix
        expected_category = get_expected_exchange_category(food.food_id, food.display_name)
        
        if not expected_category:
            stats["skipped_no_prefix"] += 1
            continue
        
        # Create exchange profile (minimal - serving_size will be calculated later)
        if dry_run:
            logger.info(
                f"  [DRY RUN] Would create exchange profile: "
                f"{food.food_id} ({food.display_name}) → {expected_category}"
            )
        else:
            try:
                exchange_profile = KBFoodExchangeProfile(
                    food_id=food.food_id,
                    exchange_category=expected_category,
                    notes=f"Auto-created based on code prefix {food.food_id[0].upper()}"
                )
                db.add(exchange_profile)
                logger.debug(f"Created exchange profile for {food.food_id} → {expected_category}")
            except Exception as e:
                logger.error(f"Error creating exchange profile for {food.food_id}: {e}")
                stats["errors"] += 1
                continue
        
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
    logger.info(f"Skipped (unknown code prefix): {stats['skipped_no_prefix']}")
    logger.info(f"Errors: {stats['errors']}")
    logger.info("=" * 70)
    logger.info("")
    logger.info("Note: serving_size_per_exchange_g should be calculated separately")
    logger.info("using import_exchange_profile_to_food_kb.py")
    logger.info("=" * 70)
    
    return stats


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Validate and correct exchange category mappings by code prefix'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run mode - only report issues without fixing'
    )
    parser.add_argument(
        '--fix',
        action='store_true',
        help='Fix incorrect mappings (ignored if --dry-run is set)'
    )
    parser.add_argument(
        '--create-missing',
        action='store_true',
        help='Create exchange profiles for foods that don\'t have them'
    )
    
    args = parser.parse_args()
    
    db = SessionLocal()
    try:
        # Validate existing mappings
        validate_exchange_categories(db, dry_run=args.dry_run, fix=args.fix)
        
        # Optionally create missing exchange profiles
        if args.create_missing:
            logger.info("")
            create_missing_exchange_profiles_by_code(db, dry_run=args.dry_run)
        
        return 0
    
    except Exception as e:
        logger.error(f"Error during validation: {e}", exc_info=True)
        if not args.dry_run:
            db.rollback()
        return 1
    
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
