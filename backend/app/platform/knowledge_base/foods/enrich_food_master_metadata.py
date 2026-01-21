"""
Enrich kb_food_master table with additional metadata fields from CSV files.

Phase 1: Populates metadata fields:
- food_type (from category mapping)
- diet_type (from category/food name inference)
- cooking_state (from food name inference)
- region (set to pan_india for IFCT data)
- source and source_reference
- last_reviewed (current date)

Phase 1.5: Creates kb_food_exchange_profile records:
- Maps CSV exchange values to IET exchange categories
- Calculates serving_size_per_exchange_g from nutrition data
- Calculates exchanges_per_common_serving from common serving size

Usage:
    From backend directory:
    python -m app.platform.knowledge_base.foods.enrich_food_master_metadata
"""

import sys
import csv
import argparse
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set

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


# Mapping from exchange category to food_type
CATEGORY_TO_FOOD_TYPE = {
    "cereals_and_millets": "grain",
    "cereals_and_millets": "grain",
    "grain_legumes": "legume",
    "fruits": "fruit",
    "green_leafy_vegetables": "vegetable",
    "other_vegetables": "vegetable",
    "roots_and_tubers": "vegetable",
    "nuts_and_oil_seeds": "nuts_seeds",
    "animal_meat": "meat",
    "poultry": "poultry",
    "marine_fish": "seafood",
    "condiments_and_spices": "spice",
    "miscellaneous_foods": "other",
}

# Mapping from exchange category to diet_type
CATEGORY_TO_DIET_TYPE = {
    "cereals_and_millets": ["vegetarian", "vegan"],
    "grain_legumes": ["vegetarian", "vegan"],
    "fruits": ["vegetarian", "vegan"],
    "green_leafy_vegetables": ["vegetarian", "vegan"],
    "other_vegetables": ["vegetarian", "vegan"],
    "roots_and_tubers": ["vegetarian", "vegan"],
    "nuts_and_oil_seeds": ["vegetarian", "vegan"],
    "animal_meat": ["non_vegetarian"],
    "poultry": ["non_vegetarian"],
    "marine_fish": ["non_vegetarian"],
    "condiments_and_spices": ["vegetarian", "vegan"],
    "miscellaneous_foods": ["vegetarian", "vegan"],  # Default, may need refinement
}

# Keywords to infer cooking_state
RAW_KEYWORDS = ["raw", "fresh", "uncooked"]
COOKED_KEYWORDS = [
    "cooked", "boiled", "fried", "roasted", "steamed", "grilled",
    "baked", "processed", "dried", "fermented", "pickled", "canned"
]

# Mapping from CSV exchange column values to IET exchange categories
# These are the 8 valid IET exchange categories
# Note: CSV values are normalized (lowercase, spaces -> underscores) before lookup
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
    "mushrooms": "vegetable_non_starchy",  # Mushrooms are non-starchy vegetables
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
    "egg_and_egg_products": None,  # Eggs don't fit standard IET categories
    "egg and egg products": None,
    "sugars": None,  # Sugars don't fit IET exchange system
}

# Starchy vegetables keywords (to refine vegetable_non_starchy)
STARCHY_VEGETABLES = ["potato", "sweet potato", "yam", "taro", "arbi", "colocasia"]

# Standard exchange nutrition values (from exchange_category_definitions_kb.json)
EXCHANGE_STANDARDS = {
    "cereal": {"calories": 80.0, "protein": 2.0, "carbs": 15.0},
    "pulse": {"calories": 100.0, "protein": 7.0, "carbs": 15.0},
    "milk": {"calories": 100.0, "protein": 6.0, "carbs": 10.0},
    "vegetable_non_starchy": {"calories": 25.0, "protein": 2.0, "carbs": 5.0},
    "vegetable_starchy": {"calories": 80.0, "protein": 2.0, "carbs": 18.0},
    "fruit": {"calories": 60.0, "protein": 1.0, "carbs": 15.0},
    "fat": {"calories": 45.0, "protein": 0.0, "carbs": 0.0},
    "nuts_seeds": {"calories": 70.0, "protein": 3.0, "carbs": 5.0},
}


def normalize_code(code: str) -> str:
    """Normalize code to uppercase for consistency."""
    if not code:
        return ""
    return code.strip().upper()


def normalize_category(exchange: str) -> Optional[str]:
    """
    Normalize Exchange column value to category (for kb_food_master.category).
    Converts to lowercase and replaces spaces with underscores.
    This is the general classification, not necessarily IET exchange category.
    """
    if not exchange:
        return None
    category = exchange.strip().lower().replace(" ", "_")
    return category if category else None


def map_to_iet_exchange_category(csv_exchange: str, food_name: str = "") -> Optional[str]:
    """
    Map CSV exchange column value to IET exchange category.
    
    Returns one of the 8 IET exchange categories, or None if food doesn't fit exchange system.
    
    Args:
        csv_exchange: Exchange value from CSV (e.g., "CEREALS AND MILLETS")
        food_name: Food name for refinement (e.g., to distinguish starchy vs non-starchy vegetables)
    
    Returns:
        IET exchange category or None
    """
    if not csv_exchange:
        return None
    
    # Normalize: lowercase, replace spaces with underscores
    normalized = csv_exchange.strip().lower().replace(" ", "_")
    
    # Get IET category
    iet_category = CSV_EXCHANGE_TO_IET_CATEGORY.get(normalized)
    
    # Refine vegetable category based on food name
    if iet_category == "vegetable_non_starchy":
        food_lower = food_name.lower()
        if any(veg in food_lower for veg in STARCHY_VEGETABLES):
            return "vegetable_starchy"
    
    return iet_category


def get_food_type_from_category(category: Optional[str]) -> Optional[str]:
    """Map exchange category to food_type."""
    if not category:
        return None
    return CATEGORY_TO_FOOD_TYPE.get(category)


def get_diet_type_from_category(category: Optional[str], food_name: str) -> Optional[List[str]]:
    """
    Infer diet_type from category and food name.
    Returns list of diet types (vegetarian, vegan, non_vegetarian).
    """
    if not category:
        # Try to infer from food name
        food_lower = food_name.lower()
        if any(term in food_lower for term in ["meat", "chicken", "fish", "egg", "poultry", "goat", "lamb", "beef", "pork"]):
            return ["non_vegetarian"]
        return ["vegetarian", "vegan"]  # Default assumption
    
    diet_types = CATEGORY_TO_DIET_TYPE.get(category, ["vegetarian", "vegan"])
    
    # Refinement: Check if vegan-safe (no animal products)
    food_lower = food_name.lower()
    if any(term in food_lower for term in ["milk", "cheese", "yogurt", "butter", "ghee", "dairy"]):
        # Contains dairy, so not vegan
        if "vegan" in diet_types:
            diet_types = [d for d in diet_types if d != "vegan"]
    
    return diet_types if diet_types else None


def infer_cooking_state(food_name: str) -> Optional[str]:
    """
    Infer cooking_state from food name.
    Returns: "raw", "cooked", or None (if ambiguous).
    """
    if not food_name:
        return None
    
    food_lower = food_name.lower()
    
    # Check for cooked keywords
    for keyword in COOKED_KEYWORDS:
        if keyword in food_lower:
            return "cooked"
    
    # Check for raw keywords
    for keyword in RAW_KEYWORDS:
        if keyword in food_lower:
            return "raw"
    
    # Default: assume raw for fresh produce, cooked for processed items
    if any(term in food_lower for term in ["dried", "processed", "canned", "pickled"]):
        return "cooked"
    
    # For fruits and vegetables without explicit state, default to raw
    return "raw"


def read_csv_file(file_path: Path) -> List[Dict[str, str]]:
    """
    Read CSV file and return list of row dictionaries.
    Handles case-insensitive column names.
    """
    rows = []
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            # Try to detect delimiter
            sample = f.read(1024)
            f.seek(0)
            sniffer = csv.Sniffer()
            delimiter = sniffer.sniff(sample).delimiter
            
            reader = csv.DictReader(f, delimiter=delimiter)
            
            # Normalize column names to handle case variations
            fieldnames = [field.strip() for field in reader.fieldnames or []]
            reader.fieldnames = fieldnames
            
            for row in reader:
                # Skip empty rows
                if not any(row.values()):
                    continue
                rows.append(row)
    
    except Exception as e:
        logger.error(f"Error reading CSV file {file_path}: {e}")
        raise
    
    return rows


def extract_food_data(row: Dict[str, str]) -> Optional[Dict[str, str]]:
    """
    Extract and normalize food data from CSV row.
    Returns dict with: code, food_name, exchange
    """
    # Handle case-insensitive column names
    code_key = None
    name_key = None
    exchange_key = None
    
    for key in row.keys():
        key_lower = key.lower().strip()
        if key_lower == "code":
            code_key = key
        elif key_lower in ["food name", "foodname"]:
            name_key = key
        elif key_lower == "exchange":
            exchange_key = key
    
    if not code_key:
        return None
    
    if not name_key:
        return None
    
    code = normalize_code(row.get(code_key, ""))
    food_name = row.get(name_key, "").strip().strip('"').strip("'").strip()
    exchange = row.get(exchange_key, "").strip() if exchange_key else ""
    
    if not code or not food_name:
        return None
    
    return {
        "code": code,
        "food_name": food_name,
        "exchange": exchange
    }


def calculate_exchange_profile(
    db: Session,
    food_id: str,
    iet_exchange_category: Optional[str],
    dry_run: bool = False
) -> bool:
    """
    Create or update kb_food_exchange_profile record.
    
    Calculates serving_size_per_exchange_g from nutrition data.
    Calculates exchanges_per_common_serving from common_serving_size_g.
    
    Returns True if created/updated, False if skipped or not applicable.
    """
    if not iet_exchange_category:
        # Food doesn't fit IET exchange system
        return False
    
    # Check if exchange standard exists
    standard = EXCHANGE_STANDARDS.get(iet_exchange_category)
    if not standard:
        logger.debug(f"No exchange standard for {iet_exchange_category}, skipping exchange profile")
        return False
    
    # Get nutrition data
    nutrition = db.query(KBFoodNutritionBase).filter(
        KBFoodNutritionBase.food_id == food_id
    ).first()
    
    if not nutrition:
        logger.debug(f"No nutrition data for {food_id}, cannot calculate exchange profile")
        return False
    
    # Need calories to calculate serving size per exchange
    calories_per_100g = float(nutrition.calories_kcal) if nutrition.calories_kcal else None
    
    # If calories are missing, try to calculate from macros
    if not calories_per_100g or calories_per_100g <= 0:
        if nutrition.macros:
            macros = nutrition.macros
            protein_g = float(macros.get('protein_g', 0) or 0)
            carbs_g = float(macros.get('carbs_g', 0) or 0)
            fat_g = float(macros.get('fat_g', 0) or 0)
            fiber_g = float(macros.get('fiber_g', 0) or 0)
            
            # Calculate calories: protein*4 + carbs*4 + fat*9 (fiber is typically subtracted from carbs)
            # Note: fiber is often not counted in calorie calculations, so we use net carbs
            if protein_g > 0 or carbs_g > 0 or fat_g > 0:
                calculated_calories = (protein_g * 4) + (carbs_g * 4) + (fat_g * 9)
                if calculated_calories > 0:
                    calories_per_100g = calculated_calories
                    logger.debug(f"Calculated calories for {food_id} from macros: {calories_per_100g:.2f} kcal")
                    # Optionally update nutrition record (but don't commit here, let caller handle it)
                    if not dry_run:
                        nutrition.calories_kcal = calculated_calories
                        db.add(nutrition)
    
    if not calories_per_100g or calories_per_100g <= 0:
        logger.debug(f"No valid calories for {food_id}, cannot calculate exchange profile")
        return False
    
    # Calculate serving size per exchange (in grams)
    # Formula: serving_size_per_exchange_g = (standard_calories / calories_per_100g) * 100
    serving_size_per_exchange_g = (standard["calories"] / calories_per_100g) * 100
    
    # Get common serving size from food_master
    food = db.query(KBFoodMaster).filter(KBFoodMaster.food_id == food_id).first()
    common_serving_size_g = float(food.common_serving_size_g) if food and food.common_serving_size_g else None
    
    # Calculate exchanges per common serving
    exchanges_per_common_serving = None
    if common_serving_size_g and common_serving_size_g > 0:
        exchanges_per_common_serving = common_serving_size_g / serving_size_per_exchange_g
    
    # Create notes
    notes = f"1 exchange = {round(serving_size_per_exchange_g, 1)}g ≈ {standard['calories']} kcal"
    
    # Check if exchange profile already exists
    exchange_profile = db.query(KBFoodExchangeProfile).filter(
        KBFoodExchangeProfile.food_id == food_id
    ).first()
    
    if exchange_profile:
        # Update existing
        updated = False
        if exchange_profile.exchange_category != iet_exchange_category:
            exchange_profile.exchange_category = iet_exchange_category
            updated = True
        if float(exchange_profile.serving_size_per_exchange_g or 0) != round(serving_size_per_exchange_g, 2):
            exchange_profile.serving_size_per_exchange_g = round(serving_size_per_exchange_g, 2)
            updated = True
        if exchanges_per_common_serving:
            if float(exchange_profile.exchanges_per_common_serving or 0) != round(exchanges_per_common_serving, 2):
                exchange_profile.exchanges_per_common_serving = round(exchanges_per_common_serving, 2)
                updated = True
        if exchange_profile.notes != notes:
            exchange_profile.notes = notes
            updated = True
        
        if not updated:
            return False  # No changes needed
        
        if dry_run:
            logger.debug(f"  [DRY RUN] Would update exchange profile for {food_id}: {iet_exchange_category}")
        else:
            db.add(exchange_profile)
    else:
        # Create new
        if dry_run:
            logger.debug(f"  [DRY RUN] Would create exchange profile for {food_id}: {iet_exchange_category}")
        else:
            exchange_profile = KBFoodExchangeProfile(
                food_id=food_id,
                exchange_category=iet_exchange_category,
                serving_size_per_exchange_g=round(serving_size_per_exchange_g, 2),
                exchanges_per_common_serving=round(exchanges_per_common_serving, 2) if exchanges_per_common_serving else None,
                notes=notes
            )
            db.add(exchange_profile)
    
    return True


def enrich_food_master(
    db: Session,
    food_id: str,
    category: Optional[str],
    food_name: str,
    csv_exchange: str,
    dry_run: bool = False
) -> Dict[str, bool]:
    """
    Enrich existing kb_food_master record with metadata fields and create exchange profile.
    
    Returns dict with 'master_updated' and 'exchange_created' boolean flags.
    """
    result = {
        "master_updated": False,
        "exchange_created": False
    }
    
    # Find existing record
    food = db.query(KBFoodMaster).filter(
        KBFoodMaster.food_id == food_id
    ).first()
    
    if not food:
        logger.debug(f"Food {food_id} not found, skipping enrichment")
        return result
    
    # Determine fields to update
    food_type = get_food_type_from_category(category)
    diet_type = get_diet_type_from_category(category, food_name)
    cooking_state = infer_cooking_state(food_name)
    
    # Track if any updates needed
    updates = {}
    
    # Update category if not set or different
    if category and food.category != category:
        updates['category'] = category
        food.category = category
    
    # Update food_type
    if food_type and food.food_type != food_type:
        updates['food_type'] = food_type
        food.food_type = food_type
    
    # Update diet_type
    if diet_type and food.diet_type != diet_type:
        updates['diet_type'] = diet_type
        food.diet_type = diet_type
    
    # Update cooking_state
    if cooking_state and food.cooking_state != cooking_state:
        updates['cooking_state'] = cooking_state
        food.cooking_state = cooking_state
    
    # Update region (IFCT data is pan_india)
    if food.region != "pan_india":
        updates['region'] = "pan_india"
        food.region = "pan_india"
    
    # Update source
    if food.source != "IFCT":
        updates['source'] = "IFCT"
        food.source = "IFCT"
    
    # Update source_reference
    source_ref = "IFCT Table 1 (Indian Food Composition Tables)"
    if food.source_reference != source_ref:
        updates['source_reference'] = source_ref
        food.source_reference = source_ref
    
    # Update last_reviewed
    today = datetime.now()
    if not food.last_reviewed or food.last_reviewed < today:
        updates['last_reviewed'] = today
        food.last_reviewed = today
    
    if updates:
        result["master_updated"] = True
        if dry_run:
            logger.debug(f"  [DRY RUN] Would update {food_id}: {list(updates.keys())}")
        else:
            db.add(food)
    
    # Create/update exchange profile
    iet_exchange_category = map_to_iet_exchange_category(csv_exchange, food_name)
    exchange_created = calculate_exchange_profile(db, food_id, iet_exchange_category, dry_run)
    result["exchange_created"] = exchange_created
    
    return result


def process_csv_file(
    db: Session,
    file_path: Path,
    dry_run: bool = False
) -> Dict[str, int]:
    """
    Process a single CSV file and enrich kb_food_master records.
    
    Returns stats dictionary.
    """
    stats = {
        "processed": 0,
        "master_updated": 0,
        "exchange_created": 0,
        "skipped": 0,
        "not_found": 0,
        "errors": 0
    }
    
    logger.info(f"Processing CSV file: {file_path.name}")
    
    try:
        rows = read_csv_file(file_path)
        stats["processed"] = len(rows)
        
        for row in rows:
            try:
                # Extract data
                food_data = extract_food_data(row)
                if not food_data:
                    stats["skipped"] += 1
                    continue
                
                code = food_data["code"]
                food_name = food_data["food_name"]
                exchange = food_data["exchange"]
                
                # Normalize category (for kb_food_master.category)
                category = normalize_category(exchange)
                
                # Enrich food master and create exchange profile
                result = enrich_food_master(db, code, category, food_name, exchange, dry_run)
                
                if result["master_updated"]:
                    stats["master_updated"] += 1
                if result["exchange_created"]:
                    stats["exchange_created"] += 1
                
                if not result["master_updated"] and not result["exchange_created"]:
                    stats["skipped"] += 1
                
                # Commit in batches
                total_updates = stats["master_updated"] + stats["exchange_created"]
                if not dry_run and total_updates % 50 == 0 and total_updates > 0:
                    db.commit()
            
            except Exception as e:
                logger.error(f"Error processing row: {e}", exc_info=True)
                stats["errors"] += 1
                if not dry_run:
                    db.rollback()
                continue
        
        # Final commit
        if not dry_run:
            db.commit()
    
    except Exception as e:
        logger.error(f"Error processing file {file_path}: {e}", exc_info=True)
        if not dry_run:
            db.rollback()
        stats["errors"] += 1
    
    return stats


def enrich_all_food_masters(
    csv_dir: Path,
    dry_run: bool = False
) -> Dict[str, int]:
    """
    Enrich all food master records from CSV files.
    
    Returns overall statistics.
    """
    csv_files = list(csv_dir.glob("*.csv"))
    
    if not csv_files:
        logger.warning(f"No CSV files found in {csv_dir}")
        return {}
    
    db = SessionLocal()
    total_stats = {
        "processed": 0,
        "master_updated": 0,
        "exchange_created": 0,
        "skipped": 0,
        "not_found": 0,
        "errors": 0
    }
    
    try:
        for csv_file in sorted(csv_files):
            stats = process_csv_file(db, csv_file, dry_run=dry_run)
            for key in total_stats:
                total_stats[key] += stats[key]
            logger.info(
                f"  {csv_file.name}: "
                f"Processed: {stats['processed']}, "
                f"Master Updated: {stats['master_updated']}, "
                f"Exchange Created: {stats['exchange_created']}, "
                f"Skipped: {stats['skipped']}, "
                f"Errors: {stats['errors']}"
            )
        
        return total_stats
    
    except Exception as e:
        logger.error(f"Error during enrichment: {e}", exc_info=True)
        if not dry_run:
            db.rollback()
        return total_stats
    
    finally:
        db.close()


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Enrich kb_food_master table with metadata fields from CSV files'
    )
    parser.add_argument(
        '--csv-dir',
        type=str,
        default=str(Path(__file__).parent / "TableOneFormatedData"),
        help='Directory containing CSV files (default: TableOneFormatedData)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run mode - show what would be updated without saving'
    )
    
    args = parser.parse_args()
    
    csv_dir = Path(args.csv_dir)
    if not csv_dir.exists():
        logger.error(f"CSV directory not found: {csv_dir}")
        return 1
    
    logger.info("=" * 70)
    logger.info("ENRICHING KB_FOOD_MASTER METADATA FROM CSV FILES")
    logger.info("=" * 70)
    logger.info(f"CSV Directory: {csv_dir}")
    logger.info(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    logger.info("=" * 70)
    logger.info("")
    
    stats = enrich_all_food_masters(csv_dir, dry_run=args.dry_run)
    
    if stats:
        logger.info("")
        logger.info("=" * 70)
        logger.info("ENRICHMENT SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Total processed: {stats['processed']}")
        logger.info(f"Master records updated: {stats['master_updated']}")
        logger.info(f"Exchange profiles created/updated: {stats['exchange_created']}")
        logger.info(f"Total skipped: {stats['skipped']}")
        logger.info(f"Total errors: {stats['errors']}")
        logger.info("=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

