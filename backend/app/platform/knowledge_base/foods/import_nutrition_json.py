"""
Import vitamins and minerals data from extracted JSON files into kb_food_nutrition_base.

Maps extracted vitamins and minerals from table2.pdf and table3.pdf into the database.
Merges data from vitamins_extracted_full.json and minerals_extracted_full.json.

Usage:
    From backend directory:
    python -m app.platform.knowledge_base.foods.import_nutrition_json \
        --vitamins vitamins_extracted_full.json \
        --minerals minerals_extracted_full.json
    
    Or with default paths:
    python -m app.platform.knowledge_base.foods.import_nutrition_json
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add backend directory to path
backend_dir = Path(__file__).parent.parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.database import SessionLocal
from app.platform.data.models.kb_food_master import KBFoodMaster
from app.platform.data.models.kb_food_nutrition_base import KBFoodNutritionBase
from app.utils.logger import logger


def load_json_file(file_path: Path) -> List[Dict[str, Any]]:
    """Load JSON file and return list of records."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            else:
                logger.error(f"Expected JSON array, got {type(data)}")
                return []
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {file_path}: {e}")
        return []
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        return []


def merge_vitamins_minerals(
    vitamins_data: List[Dict[str, Any]],
    minerals_data: List[Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    """
    Merge vitamins and minerals data by food_code.
    
    Returns a dictionary mapping food_code to merged nutrition data.
    """
    merged = {}
    
    # Process vitamins data
    for item in vitamins_data:
        food_code = item.get('food_code', '').strip().upper()
        if not food_code:
            continue
        
        if food_code not in merged:
            merged[food_code] = {
                'food_code': food_code,
                'food_name': item.get('food_name', ''),
                'vitamins': {},
                'minerals': {}
            }
        
        # Extract vitamin fields
        vitamins = merged[food_code]['vitamins']
        if item.get('vitamin_c_mg') is not None:
            vitamins['vitamin_c_mg'] = float(item['vitamin_c_mg'])
        if item.get('folate_mcg') is not None:
            vitamins['folate_mcg'] = float(item['folate_mcg'])
        if item.get('thiamine_b1_mg') is not None:
            vitamins['thiamine_b1_mg'] = float(item['thiamine_b1_mg'])
        if item.get('riboflavin_b2_mg') is not None:
            vitamins['riboflavin_b2_mg'] = float(item['riboflavin_b2_mg'])
        if item.get('niacin_b3_mg') is not None:
            vitamins['niacin_b3_mg'] = float(item['niacin_b3_mg'])
        if item.get('pantothenic_acid_b5_mg') is not None:
            vitamins['pantothenic_acid_b5_mg'] = float(item['pantothenic_acid_b5_mg'])
        if item.get('pyridoxine_b6_mg') is not None:
            vitamins['pyridoxine_b6_mg'] = float(item['pyridoxine_b6_mg'])
        if item.get('biotin_b7_mcg') is not None:
            vitamins['biotin_b7_mcg'] = float(item['biotin_b7_mcg'])
    
    # Process minerals data
    for item in minerals_data:
        food_code = item.get('food_code', '').strip().upper()
        if not food_code:
            continue
        
        if food_code not in merged:
            merged[food_code] = {
                'food_code': food_code,
                'food_name': item.get('food_name', ''),
                'vitamins': {},
                'minerals': {}
            }
        
        # Extract mineral fields
        minerals = merged[food_code]['minerals']
        if item.get('calcium_mg') is not None:
            minerals['calcium_mg'] = float(item['calcium_mg'])
        if item.get('iron_mg') is not None:
            minerals['iron_mg'] = float(item['iron_mg'])
        if item.get('magnesium_mg') is not None:
            minerals['magnesium_mg'] = float(item['magnesium_mg'])
        if item.get('phosphorus_mg') is not None:
            minerals['phosphorus_mg'] = float(item['phosphorus_mg'])
        if item.get('potassium_mg') is not None:
            minerals['potassium_mg'] = float(item['potassium_mg'])
        if item.get('sodium_mg') is not None:
            minerals['sodium_mg'] = float(item['sodium_mg'])
        if item.get('zinc_mg') is not None:
            minerals['zinc_mg'] = float(item['zinc_mg'])
        if item.get('selenium_mcg') is not None:
            minerals['selenium_mcg'] = float(item['selenium_mcg'])
        if item.get('copper_mg') is not None:
            minerals['copper_mg'] = float(item['copper_mg'])
        if item.get('manganese_mg') is not None:
            minerals['manganese_mg'] = float(item['manganese_mg'])
    
    return merged


def build_micros_json(merged_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build micros JSONB structure from merged vitamins and minerals.
    
    Maps extracted fields to database schema:
    - minerals: calcium_mg, iron_mg, magnesium_mg, phosphorus_mg, 
                potassium_mg, sodium_mg, zinc_mg, selenium_mcg
    - vitamins: vitamin_c_mg, folate_mcg
    - Note: copper_mg and manganese_mg are not in schema but we can include them
    """
    micros = {}
    
    # Add minerals (JSONB supports float/int, not Decimal directly)
    minerals = merged_data.get('minerals', {})
    if minerals.get('calcium_mg') is not None:
        micros['calcium_mg'] = float(minerals['calcium_mg'])
    if minerals.get('iron_mg') is not None:
        micros['iron_mg'] = float(minerals['iron_mg'])
    if minerals.get('magnesium_mg') is not None:
        micros['magnesium_mg'] = float(minerals['magnesium_mg'])
    if minerals.get('phosphorus_mg') is not None:
        micros['phosphorus_mg'] = float(minerals['phosphorus_mg'])
    if minerals.get('potassium_mg') is not None:
        micros['potassium_mg'] = float(minerals['potassium_mg'])
    if minerals.get('sodium_mg') is not None:
        micros['sodium_mg'] = float(minerals['sodium_mg'])
    if minerals.get('zinc_mg') is not None:
        micros['zinc_mg'] = float(minerals['zinc_mg'])
    if minerals.get('selenium_mcg') is not None:
        micros['selenium_mcg'] = float(minerals['selenium_mcg'])
    
    # Add vitamins
    vitamins = merged_data.get('vitamins', {})
    if vitamins.get('vitamin_c_mg') is not None:
        micros['vitamin_c_mg'] = float(vitamins['vitamin_c_mg'])
    if vitamins.get('folate_mcg') is not None:
        micros['folate_mcg'] = float(vitamins['folate_mcg'])
    
    # Additional fields not in schema but present in data (store as extra)
    # These could be used for future schema expansion
    extras = {}
    if minerals.get('copper_mg') is not None:
        extras['copper_mg'] = float(minerals['copper_mg'])
    if minerals.get('manganese_mg') is not None:
        extras['manganese_mg'] = float(minerals['manganese_mg'])
    if vitamins.get('thiamine_b1_mg') is not None:
        extras['thiamine_b1_mg'] = float(vitamins['thiamine_b1_mg'])
    if vitamins.get('riboflavin_b2_mg') is not None:
        extras['riboflavin_b2_mg'] = float(vitamins['riboflavin_b2_mg'])
    if vitamins.get('niacin_b3_mg') is not None:
        extras['niacin_b3_mg'] = float(vitamins['niacin_b3_mg'])
    if vitamins.get('pantothenic_acid_b5_mg') is not None:
        extras['pantothenic_acid_b5_mg'] = float(vitamins['pantothenic_acid_b5_mg'])
    if vitamins.get('pyridoxine_b6_mg') is not None:
        extras['pyridoxine_b6_mg'] = float(vitamins['pyridoxine_b6_mg'])
    if vitamins.get('biotin_b7_mcg') is not None:
        extras['biotin_b7_mcg'] = float(vitamins['biotin_b7_mcg'])
    
    # Store extras in micros with a prefix for future use
    if extras:
        micros['_extras'] = extras
    
    return micros if micros else None


def insert_or_update_nutrition(
    db: Session,
    food_id: str,
    micros: Optional[Dict[str, Any]],
    dry_run: bool = False
) -> bool:
    """
    Insert or update nutrition base record for a food.
    
    Returns True if successful, False otherwise.
    """
    try:
        # Check if nutrition record exists
        nutrition = db.query(KBFoodNutritionBase).filter(
            KBFoodNutritionBase.food_id == food_id
        ).first()
        
        if nutrition:
            # Update existing record
            if micros:
                # Merge with existing micros (preserve existing fields)
                existing_micros = nutrition.micros or {}
                if isinstance(existing_micros, dict):
                    existing_micros.update(micros)
                    nutrition.micros = existing_micros
                else:
                    nutrition.micros = micros
            
            if not dry_run:
                db.commit()
            logger.debug(f"Updated nutrition for {food_id}")
            return True
        else:
            # Insert new record
            if not micros:
                logger.warning(f"No micros data for {food_id}, skipping")
                return False
            
            nutrition = KBFoodNutritionBase(
                food_id=food_id,
                calories_kcal=None,  # Not available from extraction
                macros=None,  # Not available from extraction
                micros=micros,
                glycemic_properties=None,  # Not available from extraction
                calorie_density_kcal_per_g=None,
                protein_density_g_per_100kcal=None
            )
            
            if not dry_run:
                db.add(nutrition)
                db.commit()
            logger.debug(f"Inserted nutrition for {food_id}")
            return True
            
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Integrity error for {food_id}: {e}")
        return False
    except Exception as e:
        db.rollback()
        logger.error(f"Error processing {food_id}: {e}", exc_info=True)
        return False


def import_nutrition_data(
    vitamins_file: Path,
    minerals_file: Path,
    dry_run: bool = False
) -> Dict[str, int]:
    """
    Import nutrition data from JSON files.
    
    Returns statistics dictionary.
    """
    stats = {
        'vitamins_loaded': 0,
        'minerals_loaded': 0,
        'merged_records': 0,
        'foods_checked': 0,
        'foods_not_found': 0,
        'inserted': 0,
        'updated': 0,
        'skipped': 0,
        'errors': 0
    }
    
    logger.info("=" * 70)
    logger.info("IMPORTING NUTRITION DATA FROM JSON FILES")
    logger.info("=" * 70)
    
    # Load JSON files
    logger.info(f"Loading vitamins from: {vitamins_file}")
    vitamins_data = load_json_file(vitamins_file)
    stats['vitamins_loaded'] = len(vitamins_data)
    logger.info(f"Loaded {stats['vitamins_loaded']} vitamin records")
    
    logger.info(f"Loading minerals from: {minerals_file}")
    minerals_data = load_json_file(minerals_file)
    stats['minerals_loaded'] = len(minerals_data)
    logger.info(f"Loaded {stats['minerals_loaded']} mineral records")
    
    if not vitamins_data and not minerals_data:
        logger.error("No data loaded from either file!")
        return stats
    
    # Merge data by food_code
    logger.info("Merging vitamins and minerals data...")
    merged = merge_vitamins_minerals(vitamins_data, minerals_data)
    stats['merged_records'] = len(merged)
    logger.info(f"Merged {stats['merged_records']} unique food records")
    
    if not merged:
        logger.error("No merged records to import!")
        return stats
    
    # Connect to database
    db = SessionLocal()
    try:
        # Process each merged record
        logger.info("Processing records...")
        for idx, (food_code, merged_data) in enumerate(merged.items(), 1):
            if idx % 50 == 0:
                logger.info(f"Processing record {idx}/{stats['merged_records']}...")
            
            # Verify food exists in master table
            food = db.query(KBFoodMaster).filter(
                KBFoodMaster.food_id == food_code
            ).first()
            
            if not food:
                stats['foods_not_found'] += 1
                logger.warning(f"Food {food_code} not found in kb_food_master, skipping")
                continue
            
            stats['foods_checked'] += 1
            
            # Build micros JSON
            micros = build_micros_json(merged_data)
            
            if not micros:
                stats['skipped'] += 1
                logger.debug(f"No micros data for {food_code}, skipping")
                continue
            
            # Check if we're updating or inserting
            existing = db.query(KBFoodNutritionBase).filter(
                KBFoodNutritionBase.food_id == food_code
            ).first()
            
            # Insert or update
            success = insert_or_update_nutrition(db, food_code, micros, dry_run)
            
            if success:
                if existing:
                    stats['updated'] += 1
                else:
                    stats['inserted'] += 1
            else:
                stats['errors'] += 1
        
        logger.info("=" * 70)
        logger.info("IMPORT COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Statistics:")
        logger.info(f"  Vitamins loaded: {stats['vitamins_loaded']}")
        logger.info(f"  Minerals loaded: {stats['minerals_loaded']}")
        logger.info(f"  Merged records: {stats['merged_records']}")
        logger.info(f"  Foods checked: {stats['foods_checked']}")
        logger.info(f"  Foods not found: {stats['foods_not_found']}")
        logger.info(f"  Inserted: {stats['inserted']}")
        logger.info(f"  Updated: {stats['updated']}")
        logger.info(f"  Skipped: {stats['skipped']}")
        logger.info(f"  Errors: {stats['errors']}")
        logger.info("=" * 70)
        
    finally:
        db.close()
    
    return stats


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Import vitamins and minerals data from extracted JSON files'
    )
    parser.add_argument(
        '--vitamins',
        type=str,
        default='vitamins_extracted_full.json',
        help='Path to vitamins JSON file (default: vitamins_extracted_full.json)'
    )
    parser.add_argument(
        '--minerals',
        type=str,
        default='minerals_extracted_full.json',
        help='Path to minerals JSON file (default: minerals_extracted_full.json)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run mode - do not commit to database'
    )
    
    args = parser.parse_args()
    
    # Resolve file paths (try relative to backend directory first)
    backend_path = Path(__file__).parent.parent.parent.parent.parent
    vitamins_file = Path(args.vitamins)
    minerals_file = Path(args.minerals)
    
    # If paths are not absolute, try relative to backend directory
    if not vitamins_file.is_absolute():
        vitamins_file = backend_path / vitamins_file
    if not minerals_file.is_absolute():
        minerals_file = backend_path / minerals_file
    
    if not vitamins_file.exists():
        logger.error(f"Vitamins file not found: {vitamins_file}")
        return 1
    
    if not minerals_file.exists():
        logger.error(f"Minerals file not found: {minerals_file}")
        return 1
    
    if args.dry_run:
        logger.info("DRY RUN MODE - No changes will be saved to database")
    
    # Import data
    stats = import_nutrition_data(vitamins_file, minerals_file, dry_run=args.dry_run)
    
    if stats['errors'] > 0:
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

