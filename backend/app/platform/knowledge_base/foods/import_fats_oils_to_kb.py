"""
Import Fats & Oils from CSV into Food Knowledge Base.

This script imports fat/oil food items from Fats_Oils.csv and populates:
1. kb_food_master - Basic food identity
2. kb_food_nutrition_base - Nutrition data (calories, macros)
3. kb_food_exchange_profile - Exchange category mapping and serving sizes

Note: MNT profiles can be created separately using import_mnt_profile_to_food_kb.py

Usage:
    From backend directory:
    python -m app.platform.knowledge_base.foods.import_fats_oils_to_kb
    python -m app.platform.knowledge_base.foods.import_fats_oils_to_kb --dry-run
    python -m app.platform.knowledge_base.foods.import_fats_oils_to_kb --csv-file path/to/Fats_Oils.csv
"""

import sys
import csv
import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from decimal import Decimal

# Add backend directory to path
backend_dir = Path(__file__).parent.parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.database import SessionLocal
from app.platform.data.models.kb_food_master import KBFoodMaster
from app.platform.data.models.kb_food_nutrition_base import KBFoodNutritionBase
from app.platform.data.models.kb_food_exchange_profile import KBFoodExchangeProfile
from app.utils.logger import logger


def parse_numeric_value(value: str) -> Optional[float]:
    """Parse numeric value from CSV, handling empty strings and various formats."""
    if not value or not value.strip():
        return None
    try:
        # Remove any whitespace and convert
        cleaned = value.strip().replace(',', '')
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def get_col(row: Dict, *possible_names: str) -> Optional[str]:
    """Case-insensitive column lookup."""
    row_lower = {k.lower(): v for k, v in row.items()}
    for name in possible_names:
        if name.lower() in row_lower:
            return row_lower[name.lower()]
    return None


def load_exchange_category_definitions() -> Dict[str, Dict[str, float]]:
    """Load exchange category definitions from JSON file."""
    definitions_path = Path(__file__).parent.parent / "exchange_system" / "exchange_category_definitions_kb.json"
    
    # Fallback to core_food_groups_kb.json if exchange_category_definitions_kb.json doesn't exist
    if not definitions_path.exists():
        definitions_path = Path(__file__).parent.parent / "exchange_system" / "core_food_groups_kb.json"
    
    with open(definitions_path, 'r', encoding='utf-8') as f:
        categories = json.load(f)
    
    # Handle both formats (list or dict with core_food_groups)
    if isinstance(categories, list):
        category_list = categories
    elif isinstance(categories, dict) and "core_food_groups" in categories:
        category_list = categories["core_food_groups"]
    else:
        category_list = []
    
    # Convert to dictionary with exchange_category_id as key
    standards = {}
    for category in category_list:
        if category.get("status") == "active" or "status" not in category:
            cat_id = category.get("exchange_category_id")
            if cat_id:
                nutrition = category.get("nutrition_per_exchange", {})
                amount_per_exchange = category.get("amount_per_exchange_g", 0)
                standards[cat_id] = {
                    "calories": float(nutrition.get("calories", 0)),
                    "protein_g": float(nutrition.get("protein_g", 0)),
                    "carbs_g": float(nutrition.get("carbs_g", 0)),
                    "fat_g": float(nutrition.get("fat_g", 0)),
                    "amount_per_exchange_g": float(amount_per_exchange) if amount_per_exchange else 0.0,
                }
    
    return standards


def read_csv_file(file_path: Path) -> List[Dict[str, str]]:
    """Read CSV file and return list of row dictionaries."""
    rows = []
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            # Try to detect delimiter
            sample = f.read(1024)
            f.seek(0)
            sniffer = csv.Sniffer()
            delimiter = sniffer.sniff(sample).delimiter
            
            reader = csv.DictReader(f, delimiter=delimiter)
            
            # Normalize column names
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


def import_fats_oils(
    db: Session,
    csv_file: Path,
    dry_run: bool = False
) -> Dict[str, int]:
    """
    Import fats and oils from CSV file.
    
    Populates:
    1. kb_food_master
    2. kb_food_nutrition_base
    3. kb_food_exchange_profile
    """
    stats = {
        "processed": 0,
        "created_master": 0,
        "created_nutrition": 0,
        "created_exchange": 0,
        "updated_master": 0,
        "updated_nutrition": 0,
        "updated_exchange": 0,
        "skipped": 0,
        "errors": 0,
    }
    
    # Load exchange category definitions
    logger.info("Loading exchange category definitions...")
    exchange_standards = load_exchange_category_definitions()
    fat_standard = exchange_standards.get("fat")
    
    if not fat_standard:
        logger.error("Fat exchange standard not found in exchange category definitions!")
        return stats
    
    logger.info(f"Fat exchange standard: {fat_standard['calories']} kcal per exchange, "
                f"{fat_standard['amount_per_exchange_g']}g per exchange")
    
    # Read CSV file
    logger.info(f"Reading CSV file: {csv_file}")
    rows = read_csv_file(csv_file)
    logger.info(f"Found {len(rows)} rows")
    
    for row in rows:
        try:
            # Extract data from CSV
            code = get_col(row, "code", "Code", "CODE")
            food_name = get_col(row, "Food Name", "food name", "foodname", "FoodName")
            exchange = get_col(row, "Exchange", "exchange", "EXCHANGE")
            
            # Extract nutrition values
            protcnt = get_col(row, "PROTCNT", "protcnt", "protein")
            fatce = get_col(row, "FATCE", "fatce", "fat")
            fibtg = get_col(row, "FIBTG", "fibtg", "fiber")
            choavldf = get_col(row, "CHOAVLDF", "choavldf", "carbs", "carbohydrates")
            enerc = get_col(row, "ENERC", "enerc", "energy", "calories")
            
            # Validate required fields
            if not code or not food_name:
                logger.warning(f"Skipping row with missing code or name: {row}")
                stats["skipped"] += 1
                continue
            
            code = code.strip().upper()
            food_name = food_name.strip().strip('"').strip("'")
            
            # Parse nutrition values
            protein_g = parse_numeric_value(protcnt) if protcnt else 0.0
            fat_g = parse_numeric_value(fatce) if fatce else 0.0
            fiber_g = parse_numeric_value(fibtg) if fibtg else 0.0
            carbs_g = parse_numeric_value(choavldf) if choavldf else 0.0
            calories_kcal = parse_numeric_value(enerc) if enerc else None
            
            # For pure fats, if calories not provided, calculate from fat (9 kcal/g)
            if calories_kcal is None or calories_kcal <= 0:
                if fat_g > 0:
                    calories_kcal = fat_g * 9.0  # Fat = 9 kcal/g
                else:
                    logger.warning(f"No calories or fat for {code}, skipping")
                    stats["skipped"] += 1
                    continue
            
            stats["processed"] += 1
            
            if dry_run:
                logger.info(f"  [DRY RUN] Would import: {code} - {food_name}")
                logger.info(f"    Calories: {calories_kcal} kcal, Fat: {fat_g}g, Protein: {protein_g}g")
                stats["created_master"] += 1
                stats["created_nutrition"] += 1
                stats["created_exchange"] += 1
                continue
            
            # 1. Create or update kb_food_master
            food_master = db.query(KBFoodMaster).filter(
                KBFoodMaster.food_id == code
            ).first()
            
            if food_master:
                # Update existing
                updated = False
                if food_master.display_name != food_name:
                    food_master.display_name = food_name
                    updated = True
                if food_master.category != "fat":
                    food_master.category = "fat"
                    updated = True
                if food_master.status != "active":
                    food_master.status = "active"
                    updated = True
                
                if updated:
                    db.add(food_master)
                    stats["updated_master"] += 1
            else:
                # Create new
                food_master = KBFoodMaster(
                    food_id=code,
                    display_name=food_name,
                    category="fat",
                    status="active",
                    version="1.0"
                )
                db.add(food_master)
                stats["created_master"] += 1
            
            db.flush()  # Flush to ensure food_master exists before creating related records
            
            # 2. Create or update kb_food_nutrition_base
            nutrition = db.query(KBFoodNutritionBase).filter(
                KBFoodNutritionBase.food_id == code
            ).first()
            
            # Build macros JSON
            macros = {
                "protein_g": protein_g,
                "fat_g": fat_g,
                "fiber_g": fiber_g,
                "carbs_g": carbs_g,
            }
            
            # Calculate density metrics
            calorie_density = calories_kcal / 100.0 if calories_kcal > 0 else None
            protein_density = (protein_g / calories_kcal * 100.0) if (calories_kcal > 0 and protein_g > 0) else None
            
            if nutrition:
                # Update existing
                updated = False
                if abs(float(nutrition.calories_kcal or 0) - calories_kcal) > 0.01:
                    nutrition.calories_kcal = Decimal(str(calories_kcal))
                    updated = True
                if nutrition.macros != macros:
                    nutrition.macros = macros
                    updated = True
                if calorie_density and abs(float(nutrition.calorie_density_kcal_per_g or 0) - calorie_density) > 0.0001:
                    nutrition.calorie_density_kcal_per_g = Decimal(str(calorie_density))
                    updated = True
                if protein_density and abs(float(nutrition.protein_density_g_per_100kcal or 0) - protein_density) > 0.0001:
                    nutrition.protein_density_g_per_100kcal = Decimal(str(protein_density))
                    updated = True
                
                if updated:
                    db.add(nutrition)
                    stats["updated_nutrition"] += 1
            else:
                # Create new
                nutrition = KBFoodNutritionBase(
                    food_id=code,
                    calories_kcal=Decimal(str(calories_kcal)),
                    macros=macros,
                    calorie_density_kcal_per_g=Decimal(str(calorie_density)) if calorie_density else None,
                    protein_density_g_per_100kcal=Decimal(str(protein_density)) if protein_density else None,
                )
                db.add(nutrition)
                stats["created_nutrition"] += 1
            
            db.flush()
            
            # 3. Create or update kb_food_exchange_profile
            # Calculate serving size per exchange
            serving_size_per_exchange_g = calculate_serving_size_per_exchange(
                calories_kcal,
                fat_standard["calories"]
            )
            
            if serving_size_per_exchange_g <= 0:
                logger.warning(f"Cannot calculate serving size for {code} (calories: {calories_kcal})")
                stats["skipped"] += 1
                continue
            
            notes = f"1 exchange = {round(serving_size_per_exchange_g, 1)}g ≈ {fat_standard['calories']} kcal"
            
            exchange_profile = db.query(KBFoodExchangeProfile).filter(
                KBFoodExchangeProfile.food_id == code
            ).first()
            
            if exchange_profile:
                # Update existing
                updated = False
                if exchange_profile.exchange_category != "fat":
                    exchange_profile.exchange_category = "fat"
                    updated = True
                if abs(float(exchange_profile.serving_size_per_exchange_g or 0) - serving_size_per_exchange_g) > 0.01:
                    exchange_profile.serving_size_per_exchange_g = Decimal(str(round(serving_size_per_exchange_g, 2)))
                    updated = True
                if exchange_profile.notes != notes:
                    exchange_profile.notes = notes
                    updated = True
                
                if updated:
                    db.add(exchange_profile)
                    stats["updated_exchange"] += 1
            else:
                # Create new
                exchange_profile = KBFoodExchangeProfile(
                    food_id=code,
                    exchange_category="fat",
                    serving_size_per_exchange_g=Decimal(str(round(serving_size_per_exchange_g, 2))),
                    notes=notes
                )
                db.add(exchange_profile)
                stats["created_exchange"] += 1
            
            # Commit periodically
            if stats["processed"] % 10 == 0:
                db.commit()
                logger.info(f"Processed {stats['processed']} foods...")
        
        except IntegrityError as e:
            logger.warning(f"Integrity error for {code}: {e}")
            stats["errors"] += 1
            db.rollback()
            continue
        
        except Exception as e:
            logger.error(f"Error processing {code}: {e}", exc_info=True)
            stats["errors"] += 1
            db.rollback()
            continue
    
    # Final commit
    if not dry_run:
        db.commit()
    
    return stats


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Import fats and oils from CSV into Food Knowledge Base'
    )
    parser.add_argument(
        '--csv-file',
        type=str,
        default=str(Path(__file__).parent / "TableOneFormatedData" / "Fats_Oils.csv"),
        help='Path to Fats_Oils.csv file'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run mode - show what would be imported without saving'
    )
    
    args = parser.parse_args()
    
    csv_file = Path(args.csv_file)
    if not csv_file.exists():
        logger.error(f"CSV file not found: {csv_file}")
        return 1
    
    logger.info("=" * 70)
    logger.info("IMPORTING FATS & OILS TO FOOD KNOWLEDGE BASE")
    logger.info("=" * 70)
    logger.info(f"CSV File: {csv_file}")
    logger.info(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    logger.info("=" * 70)
    
    db = SessionLocal()
    try:
        stats = import_fats_oils(db, csv_file, dry_run=args.dry_run)
        
        logger.info("=" * 70)
        logger.info("IMPORT SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Total processed: {stats['processed']}")
        logger.info(f"kb_food_master: {stats['created_master']} created, {stats['updated_master']} updated")
        logger.info(f"kb_food_nutrition_base: {stats['created_nutrition']} created, {stats['updated_nutrition']} updated")
        logger.info(f"kb_food_exchange_profile: {stats['created_exchange']} created, {stats['updated_exchange']} updated")
        logger.info(f"Skipped: {stats['skipped']}")
        logger.info(f"Errors: {stats['errors']}")
        logger.info("=" * 70)
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Run import_mnt_profile_to_food_kb.py to create MNT profiles")
        logger.info("2. Run import_condition_compatibility_to_food_kb.py if needed")
        logger.info("=" * 70)
        
        return 0
    
    except Exception as e:
        logger.error(f"Error during import: {e}", exc_info=True)
        if not args.dry_run:
            db.rollback()
        return 1
    
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
