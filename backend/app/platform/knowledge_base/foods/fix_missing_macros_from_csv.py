"""
Fix missing macros and calories by re-importing from CSV files.

This script finds foods with empty macros/calories and re-imports them from CSV.
"""

import sys
import csv
from pathlib import Path
from typing import Dict, Optional

# Add backend directory to path
backend_dir = Path(__file__).parent.parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.platform.data.models.kb_food_master import KBFoodMaster
from app.platform.data.models.kb_food_nutrition_base import KBFoodNutritionBase
from app.utils.logger import logger
from app.platform.knowledge_base.foods.import_macros_from_csv import (
    parse_numeric_value,
    build_macros_json,
    calculate_density_metrics,
    convert_kj_to_kcal,
    normalize_code,
    read_csv_file,
)


def get_col(row: Dict, *possible_names: str) -> Optional[str]:
    """Case-insensitive column lookup."""
    row_lower = {k.lower(): v for k, v in row.items()}
    for name in possible_names:
        if name.lower() in row_lower:
            return row_lower[name.lower()]
    return None


def insert_or_update_nutrition(
    db: Session,
    food_id: str,
    calories_kcal: Optional[float],
    macros: Optional[Dict[str, float]],
    density_metrics: Dict[str, Optional[float]],
    dry_run: bool = False
) -> bool:
    """Insert or update nutrition record with macros and calories."""
    
    nutrition = db.query(KBFoodNutritionBase).filter(
        KBFoodNutritionBase.food_id == food_id
    ).first()
    
    if not nutrition:
        logger.debug(f"No nutrition record for {food_id}, skipping")
        return False
    
    updated = False
    
    # Update calories if missing
    if not nutrition.calories_kcal and calories_kcal:
        if dry_run:
            logger.debug(f"  [DRY RUN] Would set calories for {food_id}: {calories_kcal}")
        else:
            nutrition.calories_kcal = calories_kcal
        updated = True
    
    # Update macros if missing or empty
    current_macros = nutrition.macros or {}
    if macros and (not current_macros or len(current_macros) == 0):
        if dry_run:
            logger.debug(f"  [DRY RUN] Would set macros for {food_id}: {macros}")
        else:
            nutrition.macros = macros
        updated = True
    elif macros and current_macros:
        # Merge missing macro values
        merged = current_macros.copy()
        for key, value in macros.items():
            if key not in merged or not merged[key]:
                merged[key] = value
                updated = True
        if updated:
            if dry_run:
                logger.debug(f"  [DRY RUN] Would merge macros for {food_id}")
            else:
                nutrition.macros = merged
    
    # Update density metrics if missing
    if not nutrition.calorie_density_kcal_per_g and density_metrics.get('calorie_density_kcal_per_g'):
        if dry_run:
            logger.debug(f"  [DRY RUN] Would set calorie_density for {food_id}")
        else:
            nutrition.calorie_density_kcal_per_g = density_metrics['calorie_density_kcal_per_g']
        updated = True
    
    if not nutrition.protein_density_g_per_100kcal and density_metrics.get('protein_density_g_per_100kcal'):
        if dry_run:
            logger.debug(f"  [DRY RUN] Would set protein_density for {food_id}")
        else:
            nutrition.protein_density_g_per_100kcal = density_metrics['protein_density_g_per_100kcal']
        updated = True
    
    if updated and not dry_run:
        db.add(nutrition)
    
    return updated


def fix_missing_macros_from_csv(csv_dir: Path, dry_run: bool = False):
    """Fix missing macros/calories by re-importing from CSV."""
    
    db = SessionLocal()
    csv_files = list(csv_dir.glob("*.csv"))
    
    stats = {
        "files_processed": 0,
        "rows_checked": 0,
        "updated": 0,
        "skipped_no_food": 0,
        "skipped_has_data": 0,
        "errors": 0,
    }
    
    logger.info("=" * 70)
    logger.info("FIXING MISSING MACROS AND CALORIES FROM CSV")
    logger.info("=" * 70)
    logger.info(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    logger.info("")
    
    try:
        for csv_file in sorted(csv_files):
            logger.info(f"Processing: {csv_file.name}")
            stats["files_processed"] += 1
            
            rows = read_csv_file(csv_file)
            
            for row in rows:
                try:
                    stats["rows_checked"] += 1
                    
                    # Get food code
                    code = get_col(row, 'Code', 'code', 'FOOD_CODE', 'food_code')
                    if not code:
                        continue
                    
                    food_id = normalize_code(code)
                    
                    # Get nutrition record
                    nutrition = db.query(KBFoodNutritionBase).filter(
                        KBFoodNutritionBase.food_id == food_id
                    ).first()
                    
                    if not nutrition:
                        continue
                    
                    # Check if already has data
                    has_calories = nutrition.calories_kcal is not None and float(nutrition.calories_kcal or 0) > 0
                    has_macros = nutrition.macros is not None and isinstance(nutrition.macros, dict) and len(nutrition.macros) > 0 and any(v for v in nutrition.macros.values() if v)
                    
                    if has_calories and has_macros:
                        stats["skipped_has_data"] += 1
                        continue
                    
                    # Log what we're trying to fix
                    logger.debug(f"Fixing {food_id}: has_calories={has_calories}, has_macros={has_macros}")
                    
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
                    
                    # Only update if we have new data
                    if (not has_calories and calories_kcal) or (not has_macros and macros):
                        updated = insert_or_update_nutrition(
                            db, food_id, calories_kcal, macros, density_metrics, dry_run
                        )
                        if updated:
                            stats["updated"] += 1
                            
                            if stats["updated"] % 50 == 0 and not dry_run:
                                db.commit()
                                logger.info(f"  Committed {stats['updated']} updates...")
                
                except Exception as e:
                    logger.error(f"Error processing row: {e}", exc_info=True)
                    stats["errors"] += 1
                    continue
        
        if not dry_run:
            db.commit()
        
        logger.info("")
        logger.info("=" * 70)
        logger.info("SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Files processed: {stats['files_processed']}")
        logger.info(f"Rows checked: {stats['rows_checked']}")
        logger.info(f"Nutrition records updated: {stats['updated']}")
        logger.info(f"Skipped (already has data): {stats['skipped_has_data']}")
        logger.info(f"Errors: {stats['errors']}")
        logger.info("=" * 70)
        
        return stats
    
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Fix missing macros/calories from CSV')
    parser.add_argument(
        '--csv-dir',
        type=str,
        default=str(Path(__file__).parent / "TableOneFormatedData"),
        help='Directory containing CSV files'
    )
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    args = parser.parse_args()
    
    csv_dir = Path(args.csv_dir)
    if not csv_dir.exists():
        logger.error(f"CSV directory not found: {csv_dir}")
        sys.exit(1)
    
    fix_missing_macros_from_csv(csv_dir, dry_run=args.dry_run)

