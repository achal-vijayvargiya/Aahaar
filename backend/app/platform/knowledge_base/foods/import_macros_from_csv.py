"""
Import macronutrients data from CSV files into kb_food_nutrition_base.

Maps PROTCNT, FATCE, FIBTG, CHOAVLDF, and ENERC from CSV files to:
- macros JSONB (protein_g, fat_g, fiber_g, carbs_g)
- calories_kcal (converted from kJ to kcal)
- calorie_density_kcal_per_g
- protein_density_g_per_100kcal

Usage:
    From backend directory:
    python -m app.platform.knowledge_base.foods.import_macros_from_csv \
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
        "5-10" → 7.5 (midpoint)
        "123" → 123.0
        "" or "-" → None
    """
    if not value or not isinstance(value, str):
        return None
    
    value = value.strip()
    if not value or value.lower() in ['', '-', 'na', 'n/a', 'null', 'none']:
        return None
    
    # Handle ± symbol - extract first number
    if '±' in value:
        match = re.match(r'^([\d.]+)', value)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
    
    # Handle range (e.g., "5-10")
    if '-' in value and not value.startswith('-'):
        parts = value.split('-')
        if len(parts) == 2:
            try:
                start = float(parts[0].strip())
                end = float(parts[1].strip())
                return (start + end) / 2.0  # Return midpoint
            except ValueError:
                pass
    
    # Regular number
    try:
        return float(value)
    except ValueError:
        logger.debug(f"Could not parse numeric value: {value}")
        return None


def convert_kj_to_kcal(kj_value: Optional[float]) -> Optional[float]:
    """Convert kilojoules to kilocalories (1 kcal = 4.184 kJ)."""
    if kj_value is None:
        return None
    return kj_value / 4.184


def normalize_code(code: str) -> str:
    """Normalize code to uppercase for consistency."""
    if not code:
        return ""
    return code.strip().upper()


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
    
    # Case-insensitive column lookup
    row_lower = {k.lower(): v for k, v in row.items()}
    
    # Protein (PROTCNT)
    protcnt = row_lower.get('protcnt') or row_lower.get('protein')
    if protcnt:
        protein = parse_numeric_value(protcnt)
        if protein is not None:
            macros['protein_g'] = protein
    
    # Fat (FATCE)
    fatce = row_lower.get('fatce') or row_lower.get('fat')
    if fatce:
        fat = parse_numeric_value(fatce)
        if fat is not None:
            macros['fat_g'] = fat
    
    # Fiber (FIBTG)
    fibtg = row_lower.get('fibtg') or row_lower.get('fiber')
    if fibtg:
        fiber = parse_numeric_value(fibtg)
        if fiber is not None:
            macros['fiber_g'] = fiber
    
    # Carbohydrates (CHOAVLDF)
    choavldf = row_lower.get('choavldf') or row_lower.get('carbs') or row_lower.get('carbohydrates')
    if choavldf:
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
        - calorie_density_kcal_per_g: calories per gram
        - protein_density_g_per_100kcal: protein grams per 100 kcal
    """
    metrics = {
        'calorie_density_kcal_per_g': None,
        'protein_density_g_per_100kcal': None
    }
    
    # Calorie density (calories per gram)
    if calories_kcal is not None and calories_kcal > 0:
        metrics['calorie_density_kcal_per_g'] = calories_kcal / 100.0
    
    # Protein density (protein grams per 100 kcal)
    if calories_kcal is not None and calories_kcal > 0 and protein_g is not None:
        metrics['protein_density_g_per_100kcal'] = (protein_g / calories_kcal) * 100.0
    
    return metrics


def insert_or_update_nutrition(
    db: Session,
    food_id: str,
    calories_kcal: Optional[float],
    macros: Optional[Dict[str, float]],
    density_metrics: Dict[str, Optional[float]],
    dry_run: bool = False
) -> bool:
    """
    Insert or update nutrition base record for a food.
    
    Merges with existing micros data if present.
    """
    try:
        # Check if nutrition record exists
        nutrition = db.query(KBFoodNutritionBase).filter(
            KBFoodNutritionBase.food_id == food_id
        ).first()
        
        if nutrition:
            # Update existing record
            if calories_kcal is not None:
                nutrition.calories_kcal = Decimal(str(calories_kcal))
            
            if macros:
                # Merge with existing macros (preserve existing fields)
                existing_macros = nutrition.macros or {}
                if isinstance(existing_macros, dict):
                    existing_macros.update(macros)
                    nutrition.macros = existing_macros
                else:
                    nutrition.macros = macros
            
            # Update density metrics
            if density_metrics.get('calorie_density_kcal_per_g') is not None:
                nutrition.calorie_density_kcal_per_g = Decimal(
                    str(density_metrics['calorie_density_kcal_per_g'])
                )
            if density_metrics.get('protein_density_g_per_100kcal') is not None:
                nutrition.protein_density_g_per_100kcal = Decimal(
                    str(density_metrics['protein_density_g_per_100kcal'])
                )
            
            if not dry_run:
                db.commit()
            logger.debug(f"Updated nutrition macros for {food_id}")
            return True
        else:
            # Insert new record
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
            
            if not dry_run:
                db.add(nutrition)
                db.commit()
            logger.debug(f"Inserted nutrition macros for {food_id}")
            return True
            
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Integrity error for {food_id}: {e}")
        return False
    except Exception as e:
        db.rollback()
        logger.error(f"Error processing {food_id}: {e}", exc_info=True)
        return False


def process_csv_file(
    db: Session,
    file_path: Path,
    dry_run: bool = False
) -> Dict[str, int]:
    """
    Process a single CSV file and import macros.
    
    Returns statistics dictionary.
    """
    stats = {
        'rows_processed': 0,
        'foods_checked': 0,
        'foods_not_found': 0,
        'inserted': 0,
        'updated': 0,
        'skipped': 0,
        'errors': 0
    }
    
    logger.info(f"Processing CSV file: {file_path.name}")
    
    rows = read_csv_file(file_path)
    stats['rows_processed'] = len(rows)
    
    if not rows:
        logger.warning(f"No rows found in {file_path.name}")
        return stats
    
    # Case-insensitive column lookup helper
    def get_col(row: Dict, *possible_names: str) -> Optional[str]:
        row_lower = {k.lower(): v for k, v in row.items()}
        for name in possible_names:
            if name.lower() in row_lower:
                return row_lower[name.lower()]
        return None
    
    # Process each row
    for row in rows:
        # Get food code
        code = get_col(row, 'Code', 'code', 'FOOD_CODE', 'food_code')
        if not code:
            stats['skipped'] += 1
            continue
        
        food_id = normalize_code(code)
        if not food_id:
            stats['skipped'] += 1
            continue
        
        # Verify food exists in master table
        food = db.query(KBFoodMaster).filter(
            KBFoodMaster.food_id == food_id
        ).first()
        
        if not food:
            stats['foods_not_found'] += 1
            logger.debug(f"Food {food_id} not found in kb_food_master, skipping")
            continue
        
        stats['foods_checked'] += 1
        
        # Get ENERC (energy in kJ)
        enerc = get_col(row, 'ENERC', 'enerc', 'ENERGY', 'energy', 'ENERGY_KJ', 'energy_kj')
        calories_kcal = None
        if enerc:
            kj_value = parse_numeric_value(enerc)
            if kj_value is not None:
                calories_kcal = convert_kj_to_kcal(kj_value)
        
        # Build macros JSON
        macros = build_macros_json(row)
        
        # Calculate density metrics
        protein_g = macros.get('protein_g') if macros else None
        density_metrics = calculate_density_metrics(calories_kcal, protein_g)
        
        # Skip if no data at all
        if not macros and calories_kcal is None:
            stats['skipped'] += 1
            logger.debug(f"No macro or calorie data for {food_id}, skipping")
            continue
        
        # Insert or update
        success = insert_or_update_nutrition(
            db, food_id, calories_kcal, macros, density_metrics, dry_run
        )
        
        if success:
            # Check if we're updating or inserting (simplified check)
            existing = db.query(KBFoodNutritionBase).filter(
                KBFoodNutritionBase.food_id == food_id
            ).first()
            if existing and (existing.calories_kcal or existing.macros):
                stats['updated'] += 1
            else:
                stats['inserted'] += 1
        else:
            stats['errors'] += 1
    
    return stats


def import_macros_from_csv(
    csv_dir: Path,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Import macros data from all CSV files in directory.
    
    Returns overall statistics dictionary.
    """
    overall_stats = {
        'files_processed': 0,
        'rows_processed': 0,
        'foods_checked': 0,
        'foods_not_found': 0,
        'inserted': 0,
        'updated': 0,
        'skipped': 0,
        'errors': 0
    }
    
    logger.info("=" * 70)
    logger.info("IMPORTING MACROS DATA FROM CSV FILES")
    logger.info("=" * 70)
    logger.info(f"CSV Directory: {csv_dir}")
    
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
            file_stats = process_csv_file(db, csv_file, dry_run)
            
            # Aggregate statistics
            overall_stats['files_processed'] += 1
            overall_stats['rows_processed'] += file_stats['rows_processed']
            overall_stats['foods_checked'] += file_stats['foods_checked']
            overall_stats['foods_not_found'] += file_stats['foods_not_found']
            overall_stats['inserted'] += file_stats['inserted']
            overall_stats['updated'] += file_stats['updated']
            overall_stats['skipped'] += file_stats['skipped']
            overall_stats['errors'] += file_stats['errors']
            
            logger.info(f"  Rows: {file_stats['rows_processed']}, "
                       f"Checked: {file_stats['foods_checked']}, "
                       f"Inserted: {file_stats['inserted']}, "
                       f"Updated: {file_stats['updated']}, "
                       f"Skipped: {file_stats['skipped']}, "
                       f"Errors: {file_stats['errors']}")
        
        logger.info("\n" + "=" * 70)
        logger.info("IMPORT COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Overall Statistics:")
        logger.info(f"  Files processed: {overall_stats['files_processed']}")
        logger.info(f"  Rows processed: {overall_stats['rows_processed']}")
        logger.info(f"  Foods checked: {overall_stats['foods_checked']}")
        logger.info(f"  Foods not found: {overall_stats['foods_not_found']}")
        logger.info(f"  Inserted: {overall_stats['inserted']}")
        logger.info(f"  Updated: {overall_stats['updated']}")
        logger.info(f"  Skipped: {overall_stats['skipped']}")
        logger.info(f"  Errors: {overall_stats['errors']}")
        logger.info("=" * 70)
        
    finally:
        db.close()
    
    return overall_stats


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Import macronutrients data from CSV files'
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
    
    # Import data
    stats = import_macros_from_csv(csv_dir, dry_run=args.dry_run)
    
    if stats['errors'] > 0:
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

