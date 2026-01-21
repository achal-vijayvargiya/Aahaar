"""
Import macro details and energy from CSV files into food KB.

This script:
1. Reads CSV files from TableOneFormatedData directory
2. Ensures foods exist in kb_food_master (creates basic record if missing - only food_id, display_name, category)
3. Stores macros and energy in kb_food_nutrition_base table:
   - Macros (protein_g, fat_g, fiber_g, carbs_g) from PROTCNT, FATCE, FIBTG, CHOAVLDF
   - Energy (calories_kcal) converted from ENERC (kJ) to kcal
   - Density metrics (calorie_density_kcal_per_g, protein_density_g_per_100kcal)

IMPORTANT: Macros and calories are stored in kb_food_nutrition_base, NOT in kb_food_master.
The kb_food_master table only stores basic food identity (food_id, display_name, category).

Mapping: CSV 'code' field → kb_food_master.food_id → kb_food_nutrition_base.food_id

Usage:
    From backend directory:
    python -m app.platform.knowledge_base.foods.import_macros_to_food_kb \
        --csv-dir app/platform/knowledge_base/foods/TableOneFormatedData
"""

import sys
import csv
import argparse
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from decimal import Decimal, InvalidOperation

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


def parse_numeric_value(value: str) -> Optional[float]:
    """
    Parse numeric value from CSV, handling ± symbols and ranges.
    
    Examples:
        "20.33±0.50" → 20.33
        "261±15" → 261.0
        "123" → 123.0
        "" or "-" → None
    """
    if not value or not isinstance(value, str):
        return None
    
    value = value.strip()
    if not value or value.lower() in ['', '-', 'na', 'n/a', 'null', 'none']:
        return None
    
    # Handle ± symbol (also check for encoding issues with ±)
    # Try multiple representations of ± symbol
    plus_minus_chars = ['±', '\u00B1', '\xB1']  # ± in different encodings
    has_plus_minus = any(char in value for char in plus_minus_chars)
    
    if has_plus_minus:
        # Extract first number before ± symbol
        match = re.match(r'^([\d.]+)', value)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
    
    # Handle range (e.g., "5-10") - but be careful not to confuse with negative numbers
    # Only treat as range if there's a space or it looks like "num-num" pattern
    if '-' in value and not value.startswith('-'):
        # Check if it looks like a range (two numbers separated by dash)
        range_pattern = r'^([\d.]+)\s*-\s*([\d.]+)'
        match = re.match(range_pattern, value)
        if match:
            try:
                start = float(match.group(1))
                end = float(match.group(2))
                return (start + end) / 2.0  # Return midpoint
            except ValueError:
                pass
    
    # Regular number - try to extract first number if there are non-numeric chars
    # This handles cases like "261�15" where encoding is broken
    number_match = re.match(r'^([\d.]+)', value)
    if number_match:
        try:
            return float(number_match.group(1))
        except ValueError:
            pass
    
    # Last resort: try parsing the whole value
    try:
        return float(value)
    except ValueError:
        logger.debug(f"Could not parse numeric value: {value!r}")
        return None


def convert_kj_to_kcal(kj_value: Optional[float]) -> Optional[float]:
    """
    Convert kilojoules to kilocalories.
    
    Formula: 1 kcal = 4.184 kJ
    Therefore: kcal = kJ / 4.184
    """
    if kj_value is None:
        return None
    return kj_value / 4.184


def normalize_code(code: str) -> str:
    """Normalize code to uppercase for consistency."""
    if not code:
        return ""
    return code.strip().upper()


def normalize_category(exchange: str) -> Optional[str]:
    """
    Normalize exchange category name to standard format.
    
    Maps CSV exchange categories to standard category names.
    """
    if not exchange:
        return None
    
    exchange_lower = exchange.lower().strip()
    
    # Map exchange categories to standard categories
    category_map = {
        'cereals and millets': 'cereal',
        'cereals_and_millets': 'cereal',
        'grain legumes': 'pulse',
        'grain_legumes': 'pulse',
        'green leafy vegetables': 'vegetable_non_starchy',
        'green_leafy_vegetables': 'vegetable_non_starchy',
        'other vegetables': 'vegetable_non_starchy',
        'other_vegetables': 'vegetable_non_starchy',
        'roots and tubers': 'vegetable_starchy',
        'roots_and_tubers': 'vegetable_starchy',
        'fruits': 'fruit',
        'nuts and oil seeds': 'nuts_seeds',
        'nuts_and_oil_seeds': 'nuts_seeds',
        'animal meat': 'animal_protein',
        'animal_meat': 'animal_protein',
        'poultry': 'animal_protein',
        'marine fish': 'animal_protein',
        'marine_fish': 'animal_protein',
        'condiments and spices': 'condiment',
        'condiments_and_spices': 'condiment',
        'miscellaneous foods': 'other',
        'miscellaneous_foods': 'other',
    }
    
    return category_map.get(exchange_lower, exchange_lower.replace(' ', '_'))


def read_csv_file(file_path: Path) -> List[Dict[str, Any]]:
    """
    Read CSV file and return list of row dictionaries.
    Handles case-insensitive column names and various delimiters.
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
                
                # Normalize row - trim whitespace from values
                normalized_row = {k: (v.strip() if v else '') for k, v in row.items()}
                rows.append(normalized_row)
    
    except Exception as e:
        logger.error(f"Error reading CSV file {file_path}: {e}")
    
    return rows


def get_col(row: Dict, *possible_names: str) -> Optional[str]:
    """Case-insensitive column lookup."""
    row_lower = {k.lower(): v for k, v in row.items()}
    for name in possible_names:
        if name.lower() in row_lower:
            return row_lower[name.lower()]
    return None


def build_macros_json(row: Dict[str, str]) -> Optional[Dict[str, float]]:
    """
    Build macros JSONB structure from CSV row.
    
    Maps:
    - PROTCNT → protein_g
    - FATCE → fat_g
    - FIBTG → fiber_g
    - CHOAVLDF → carbs_g
    """
    macros = {}
    
    # Protein (PROTCNT)
    protcnt = get_col(row, 'PROTCNT', 'protcnt', 'protein')
    if protcnt and protcnt.strip():  # Check for non-empty string
        protein = parse_numeric_value(protcnt)
        if protein is not None:
            macros['protein_g'] = protein
    
    # Fat (FATCE)
    fatce = get_col(row, 'FATCE', 'fatce', 'fat')
    if fatce and fatce.strip():  # Check for non-empty string
        fat = parse_numeric_value(fatce)
        if fat is not None:
            macros['fat_g'] = fat
    
    # Fiber (FIBTG)
    fibtg = get_col(row, 'FIBTG', 'fibtg', 'fiber')
    if fibtg and fibtg.strip():  # Check for non-empty string
        fiber = parse_numeric_value(fibtg)
        if fiber is not None:
            macros['fiber_g'] = fiber
    
    # Carbohydrates (CHOAVLDF)
    choavldf = get_col(row, 'CHOAVLDF', 'choavldf', 'carbs', 'carbohydrates')
    if choavldf and choavldf.strip():  # Check for non-empty string
        carbs = parse_numeric_value(choavldf)
        if carbs is not None:
            macros['carbs_g'] = carbs
    
    return macros if macros else None


def calculate_density_metrics(
    calories_kcal: Optional[float],
    protein_g: Optional[float]
) -> Dict[str, Optional[float]]:
    """
    Calculate calorie and protein density metrics.
    
    Returns:
        - calorie_density_kcal_per_g: calories per gram (per 100g)
        - protein_density_g_per_100kcal: protein grams per 100 kcal
    """
    metrics = {
        'calorie_density_kcal_per_g': None,
        'protein_density_g_per_100kcal': None
    }
    
    # Calorie density (calories per gram) - values are per 100g, so divide by 100
    if calories_kcal is not None and calories_kcal > 0:
        metrics['calorie_density_kcal_per_g'] = calories_kcal / 100.0
    
    # Protein density (protein grams per 100 kcal)
    if calories_kcal is not None and calories_kcal > 0 and protein_g is not None:
        metrics['protein_density_g_per_100kcal'] = (protein_g / calories_kcal) * 100.0
    
    return metrics


def ensure_food_master_exists(
    db: Session,
    food_id: str,
    food_name: str,
    exchange_category: Optional[str],
    dry_run: bool = False
) -> bool:
    """
    Ensure food exists in kb_food_master, create if missing.
    
    NOTE: This only creates a basic food record (food_id, display_name, category).
    Macros and calories are stored separately in kb_food_nutrition_base.
    
    Returns True if food exists or was created, False on error.
    """
    # Check if food already exists
    food = db.query(KBFoodMaster).filter(
        KBFoodMaster.food_id == food_id
    ).first()
    
    if food:
        return True
    
    # Create new food master entry
    category = normalize_category(exchange_category) if exchange_category else None
    
    if dry_run:
        logger.debug(f"  [DRY RUN] Would create food_master: {food_id} - {food_name} (category: {category})")
        return True
    
    try:
        food_master = KBFoodMaster(
            food_id=food_id,
            display_name=food_name,
            category=category,
            status='active',
            version='1.0'
        )
        db.add(food_master)
        db.flush()  # Flush to get ID without committing
        logger.debug(f"Created food_master entry: {food_id}")
        return True
    except IntegrityError:
        db.rollback()
        # Food might have been created by another process, check again
        food = db.query(KBFoodMaster).filter(
            KBFoodMaster.food_id == food_id
        ).first()
        if food:
            return True
        logger.error(f"Failed to create food_master for {food_id}")
        return False
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating food_master for {food_id}: {e}")
        return False


def insert_or_update_nutrition(
    db: Session,
    food_id: str,
    calories_kcal: Optional[float],
    macros: Optional[Dict[str, float]],
    density_metrics: Dict[str, Optional[float]],
    dry_run: bool = False
) -> bool:
    """
    Insert or update nutrition record in kb_food_nutrition_base table.
    
    Stores macros and calories in kb_food_nutrition_base (NOT in kb_food_master).
    Merges with existing macros/micros data if present.
    """
    try:
        # Check if nutrition record exists
        nutrition = db.query(KBFoodNutritionBase).filter(
            KBFoodNutritionBase.food_id == food_id
        ).first()
        
        if nutrition:
            # Update existing record
            updated = False
            
            if calories_kcal is not None:
                nutrition.calories_kcal = Decimal(str(calories_kcal))
                updated = True
            
            if macros:
                # Merge with existing macros (preserve existing fields)
                existing_macros = nutrition.macros or {}
                if isinstance(existing_macros, dict):
                    existing_macros.update(macros)
                    nutrition.macros = existing_macros
                else:
                    nutrition.macros = macros
                updated = True
            
            # Update density metrics
            if density_metrics.get('calorie_density_kcal_per_g') is not None:
                nutrition.calorie_density_kcal_per_g = Decimal(
                    str(density_metrics['calorie_density_kcal_per_g'])
                )
                updated = True
            if density_metrics.get('protein_density_g_per_100kcal') is not None:
                nutrition.protein_density_g_per_100kcal = Decimal(
                    str(density_metrics['protein_density_g_per_100kcal'])
                )
                updated = True
            
            if updated and not dry_run:
                db.add(nutrition)
            logger.debug(f"Updated nutrition for {food_id}")
            return True
        else:
            # Insert new record
            if dry_run:
                logger.debug(f"  [DRY RUN] Would create nutrition for {food_id}")
                return True
            
            nutrition = KBFoodNutritionBase(
                food_id=food_id,
                calories_kcal=Decimal(str(calories_kcal)) if calories_kcal is not None else None,
                macros=macros,
                micros=None,  # Not set here, should be set separately
                glycemic_properties=None,
                calorie_density_kcal_per_g=Decimal(
                    str(density_metrics['calorie_density_kcal_per_g'])
                ) if density_metrics.get('calorie_density_kcal_per_g') is not None else None,
                protein_density_g_per_100kcal=Decimal(
                    str(density_metrics['protein_density_g_per_100kcal'])
                ) if density_metrics.get('protein_density_g_per_100kcal') is not None else None
            )
            
            db.add(nutrition)
            logger.debug(f"Inserted nutrition for {food_id}")
            return True
            
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Integrity error for {food_id}: {e}")
        return False
    except Exception as e:
        db.rollback()
        logger.error(f"Error processing nutrition for {food_id}: {e}", exc_info=True)
        return False


def process_csv_file(
    db: Session,
    file_path: Path,
    dry_run: bool = False,
    verbose: bool = False
) -> Dict[str, int]:
    """
    Process a single CSV file and import macros/energy into kb_food_nutrition_base.
    
    Ensures food exists in kb_food_master first (required for foreign key),
    then stores macros and calories in kb_food_nutrition_base.
    
    Returns statistics dictionary.
    """
    stats = {
        'rows_processed': 0,
        'foods_created': 0,
        'foods_existed': 0,
        'nutrition_inserted': 0,
        'nutrition_updated': 0,
        'skipped': 0,
        'errors': 0
    }
    
    logger.info(f"Processing CSV file: {file_path.name}")
    
    rows = read_csv_file(file_path)
    stats['rows_processed'] = len(rows)
    
    if not rows:
        logger.warning(f"No rows found in {file_path.name}")
        return stats
    
    # Process each row
    for row in rows:
        try:
            # Get food code (handle both 'code' and 'Code')
            code = get_col(row, 'Code', 'code', 'FOOD_CODE', 'food_code')
            if not code:
                stats['skipped'] += 1
                continue
            
            food_id = normalize_code(code)
            if not food_id:
                stats['skipped'] += 1
                continue
            
            # Get food name
            food_name = get_col(row, 'Food Name', 'food name', 'food_name', 'name')
            if not food_name:
                food_name = f"Food {food_id}"  # Fallback name
            
            # Get exchange category
            exchange = get_col(row, 'Exchange', 'exchange', 'category')
            
            # Ensure food exists in master table
            food_existed = db.query(KBFoodMaster).filter(
                KBFoodMaster.food_id == food_id
            ).first() is not None
            
            success = ensure_food_master_exists(db, food_id, food_name, exchange, dry_run)
            if not success:
                stats['errors'] += 1
                continue
            
            if not food_existed:
                stats['foods_created'] += 1
            else:
                stats['foods_existed'] += 1
            
            # Get ENERC (energy in kJ) and convert to kcal
            enerc = get_col(row, 'ENERC', 'enerc', 'ENERGY', 'energy', 'ENERGY_KJ', 'energy_kj')
            calories_kcal = None
            if enerc and enerc.strip():  # Check for non-empty string
                kj_value = parse_numeric_value(enerc)
                if kj_value is not None:
                    calories_kcal = convert_kj_to_kcal(kj_value)
                    logger.debug(f"Converted {kj_value} kJ to {calories_kcal:.2f} kcal for {food_id}")
                else:
                    logger.debug(f"Failed to parse energy value '{enerc}' for {food_id}")
            else:
                logger.debug(f"No ENERC value found for {food_id} (column value: '{enerc}')")
            
            # Build macros JSON
            macros = build_macros_json(row)
            
            # Log macro parsing results for debugging
            if not macros:
                logger.debug(f"No macros parsed for {food_id} - PROTCNT: {get_col(row, 'PROTCNT')}, FATCE: {get_col(row, 'FATCE')}, FIBTG: {get_col(row, 'FIBTG')}, CHOAVLDF: {get_col(row, 'CHOAVLDF')}")
            
            # Calculate density metrics
            protein_g = macros.get('protein_g') if macros else None
            density_metrics = calculate_density_metrics(calories_kcal, protein_g)
            
            # Skip if no data at all (both macros and calories missing)
            if not macros and calories_kcal is None:
                stats['skipped'] += 1
                # Show detailed info about why it was skipped
                enerc_raw = get_col(row, 'ENERC', 'enerc', 'ENERGY', 'energy', 'ENERGY_KJ', 'energy_kj')
                protcnt_raw = get_col(row, 'PROTCNT', 'protcnt', 'protein')
                fatce_raw = get_col(row, 'FATCE', 'fatce', 'fat')
                fibtg_raw = get_col(row, 'FIBTG', 'fibtg', 'fiber')
                choavldf_raw = get_col(row, 'CHOAVLDF', 'choavldf', 'carbs', 'carbohydrates')
                
                if verbose:
                    logger.info(f"Skipping {food_id} ({food_name}):")
                    logger.info(f"  ENERC raw: '{enerc_raw}' -> parsed: {calories_kcal}")
                    logger.info(f"  PROTCNT raw: '{protcnt_raw}'")
                    logger.info(f"  FATCE raw: '{fatce_raw}'")
                    logger.info(f"  FIBTG raw: '{fibtg_raw}'")
                    logger.info(f"  CHOAVLDF raw: '{choavldf_raw}'")
                    logger.info(f"  Macros parsed: {macros}")
                else:
                    logger.warning(f"Skipping {food_id}: No macro or calorie data - ENERC: '{enerc_raw}', macros: {macros}")
                continue
            
            # Check if nutrition record already exists
            nutrition_exists = db.query(KBFoodNutritionBase).filter(
                KBFoodNutritionBase.food_id == food_id
            ).first() is not None
            
            # Insert or update nutrition
            success = insert_or_update_nutrition(
                db, food_id, calories_kcal, macros, density_metrics, dry_run
            )
            
            if success:
                if nutrition_exists:
                    stats['nutrition_updated'] += 1
                else:
                    stats['nutrition_inserted'] += 1
                
                # Commit periodically
                if (stats['nutrition_inserted'] + stats['nutrition_updated']) % 50 == 0 and not dry_run:
                    db.commit()
                    logger.info(f"  Committed {stats['nutrition_inserted'] + stats['nutrition_updated']} nutrition records...")
            else:
                stats['errors'] += 1
        
        except Exception as e:
            logger.error(f"Error processing row: {e}", exc_info=True)
            stats['errors'] += 1
            continue
    
    return stats


def import_macros_to_food_kb(
    csv_dir: Path,
    dry_run: bool = False,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Import macros and energy data from all CSV files into kb_food_nutrition_base.
    
    Macros and calories are stored in kb_food_nutrition_base table.
    Basic food records are created/updated in kb_food_master as needed.
    
    Returns overall statistics dictionary.
    """
    overall_stats = {
        'files_processed': 0,
        'rows_processed': 0,
        'foods_created': 0,
        'foods_existed': 0,
        'nutrition_inserted': 0,
        'nutrition_updated': 0,
        'skipped': 0,
        'errors': 0
    }
    
    logger.info("=" * 70)
    logger.info("IMPORTING MACROS AND ENERGY DATA FROM CSV FILES")
    logger.info("=" * 70)
    logger.info(f"CSV Directory: {csv_dir}")
    logger.info(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    
    # Find all CSV files
    csv_files = list(csv_dir.glob("*.csv"))
    if not csv_files:
        logger.error(f"No CSV files found in {csv_dir}")
        return overall_stats
    
    logger.info(f"Found {len(csv_files)} CSV files")
    logger.info("=" * 70)
    
    # Connect to database
    db = SessionLocal()
    try:
        # Process each CSV file
        for csv_file in sorted(csv_files):
            logger.info(f"\nProcessing: {csv_file.name}")
            file_stats = process_csv_file(db, csv_file, dry_run, verbose)
            
            # Aggregate statistics
            overall_stats['files_processed'] += 1
            overall_stats['rows_processed'] += file_stats['rows_processed']
            overall_stats['foods_created'] += file_stats['foods_created']
            overall_stats['foods_existed'] += file_stats['foods_existed']
            overall_stats['nutrition_inserted'] += file_stats['nutrition_inserted']
            overall_stats['nutrition_updated'] += file_stats['nutrition_updated']
            overall_stats['skipped'] += file_stats['skipped']
            overall_stats['errors'] += file_stats['errors']
            
            logger.info(f"  Rows: {file_stats['rows_processed']}, "
                       f"Foods created: {file_stats['foods_created']}, "
                       f"Foods existed: {file_stats['foods_existed']}, "
                       f"Nutrition inserted: {file_stats['nutrition_inserted']}, "
                       f"Nutrition updated: {file_stats['nutrition_updated']}, "
                       f"Skipped: {file_stats['skipped']}, "
                       f"Errors: {file_stats['errors']}")
        
        if not dry_run:
            db.commit()
        
        logger.info("\n" + "=" * 70)
        logger.info("IMPORT COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Overall Statistics:")
        logger.info(f"  Files processed: {overall_stats['files_processed']}")
        logger.info(f"  Rows processed: {overall_stats['rows_processed']}")
        logger.info(f"  Foods created: {overall_stats['foods_created']}")
        logger.info(f"  Foods already existed: {overall_stats['foods_existed']}")
        logger.info(f"  Nutrition records inserted: {overall_stats['nutrition_inserted']}")
        logger.info(f"  Nutrition records updated: {overall_stats['nutrition_updated']}")
        logger.info(f"  Skipped: {overall_stats['skipped']}")
        logger.info(f"  Errors: {overall_stats['errors']}")
        logger.info("=" * 70)
    
    finally:
        db.close()
    
    return overall_stats


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Import macronutrients and energy data from CSV files into food KB'
    )
    parser.add_argument(
        '--csv-dir',
        type=str,
        default='app/platform/knowledge_base/foods/TableOneFormatedData',
        help='Directory containing CSV files (default: app/platform/knowledge_base/foods/TableOneFormatedData)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run mode - do not commit to database'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose mode - show detailed logging for skipped records'
    )
    
    args = parser.parse_args()
    
    # Resolve CSV directory path
    backend_path = Path(__file__).parent.parent.parent.parent.parent
    csv_dir = Path(args.csv_dir)
    
    # If path is not absolute, try relative to backend directory
    if not csv_dir.is_absolute():
        csv_dir = backend_path / csv_dir
    
    if not csv_dir.exists():
        logger.error(f"CSV directory not found: {csv_dir}")
        return 1
    
    if not csv_dir.is_dir():
        logger.error(f"Path is not a directory: {csv_dir}")
        return 1
    
    if args.dry_run:
        logger.info("DRY RUN MODE - No changes will be saved to database")
    if args.verbose:
        logger.info("VERBOSE MODE - Detailed logging enabled")
    
    # Import data
    stats = import_macros_to_food_kb(csv_dir, dry_run=args.dry_run, verbose=args.verbose)
    
    if stats['errors'] > 0:
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

