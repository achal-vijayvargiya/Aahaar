"""
Import serving information from structured CSV into kb_food_master.

This script reads food_serving_info.csv and updates:
- kb_food_master.common_serving_unit
- kb_food_master.common_serving_size_g

Only updates records where these fields are NULL (or can force update with --force).

Usage:
    python -m app.platform.knowledge_base.foods.import_serving_info_to_food_kb
    python -m app.platform.knowledge_base.foods.import_serving_info_to_food_kb --force
"""

import sys
import csv
import argparse
from pathlib import Path
from typing import Dict, Optional
from decimal import Decimal, InvalidOperation

# Add backend directory to path
backend_dir = Path(__file__).parent.parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.platform.data.models.kb_food_master import KBFoodMaster
from app.utils.logger import logger


def normalize_serving_unit(unit: str) -> Optional[str]:
    """
    Normalize serving unit to standard values.
    
    Maps variations to standard units:
    - small, sm -> small
    - medium, med -> medium
    - large, lg -> large
    - cup -> cup
    - pieces, pcs, pc, piece -> pieces
    - tsp, teaspoon -> tsp
    - tbsp, tablespoon -> tbsp
    - g, gram, grams -> g
    """
    if not unit:
        return None
    
    unit_lower = unit.strip().lower()
    
    unit_map = {
        'small': 'small',
        'sm': 'small',
        'medium': 'medium',
        'med': 'medium',
        'large': 'large',
        'lg': 'large',
        'cup': 'cup',
        'cups': 'cup',
        'pieces': 'pieces',
        'pcs': 'pieces',
        'pc': 'pieces',
        'piece': 'pieces',
        'tsp': 'tsp',
        'teaspoon': 'tsp',
        'tbsp': 'tbsp',
        'tablespoon': 'tbsp',
        'g': 'g',
        'gram': 'g',
        'grams': 'g',
        'pellet': 'pellet',
        'pellets': 'pellet',
    }
    
    return unit_map.get(unit_lower, unit_lower)


def read_serving_info_csv(csv_file: Path) -> Dict[str, Dict[str, any]]:
    """
    Read serving info CSV and return mapping: {food_id: {serving_size_g, serving_unit}}
    
    Skips rows where food_id is empty (unmatched items).
    """
    serving_info = {}
    
    if not csv_file.exists():
        logger.error(f"CSV file not found: {csv_file}")
        return serving_info
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            food_id = row.get('food_id', '').strip().upper()
            
            # Skip unmatched items (empty food_id)
            if not food_id or food_id == 'UNMATCHED':
                continue
            
            try:
                serving_size_g = float(row.get('serving_size_g', 0))
                serving_unit = normalize_serving_unit(row.get('serving_unit', ''))
                
                if serving_size_g > 0:
                    serving_info[food_id] = {
                        'serving_size_g': serving_size_g,
                        'serving_unit': serving_unit or 'g',  # Default to 'g' if not specified
                        'food_name': row.get('food_name', ''),
                        'category': row.get('category', ''),
                    }
            except (ValueError, KeyError) as e:
                logger.warning(f"Skipping invalid row: {row.get('food_name', 'unknown')} - {e}")
                continue
    
    return serving_info


def update_food_master_serving_info(
    db: Session,
    serving_info: Dict[str, Dict[str, any]],
    force_update: bool = False,
    dry_run: bool = False
) -> Dict[str, int]:
    """
    Update kb_food_master with serving information.
    
    Returns statistics dictionary.
    """
    stats = {
        'total_in_csv': len(serving_info),
        'foods_found': 0,
        'foods_not_found': 0,
        'updated': 0,
        'skipped_already_set': 0,
        'errors': 0
    }
    
    logger.info("=" * 70)
    logger.info("UPDATING FOOD MASTER WITH SERVING INFORMATION")
    logger.info("=" * 70)
    logger.info(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    logger.info(f"Force update: {force_update}")
    logger.info("")
    
    for food_id, info in serving_info.items():
        try:
            # Find food in database
            food = db.query(KBFoodMaster).filter(
                KBFoodMaster.food_id == food_id
            ).first()
            
            if not food:
                stats['foods_not_found'] += 1
                logger.debug(f"Food {food_id} not found in database")
                continue
            
            stats['foods_found'] += 1
            
            # Check if already has values
            has_unit = food.common_serving_unit is not None and food.common_serving_unit.strip()
            has_size = food.common_serving_size_g is not None
            
            if has_unit and has_size and not force_update:
                stats['skipped_already_set'] += 1
                logger.debug(f"Skipping {food_id} ({food.display_name}): already has serving info")
                continue
            
            # Prepare updates
            updates = {}
            
            if not has_unit or force_update:
                updates['common_serving_unit'] = info['serving_unit']
            
            if not has_size or force_update:
                updates['common_serving_size_g'] = Decimal(str(info['serving_size_g']))
            
            if updates:
                if dry_run:
                    logger.info(f"[DRY RUN] Would update {food_id} ({food.display_name}): {updates}")
                else:
                    for key, value in updates.items():
                        setattr(food, key, value)
                    db.add(food)
                    logger.debug(f"Updated {food_id} ({food.display_name}): {updates}")
                
                stats['updated'] += 1
                
                # Commit periodically
                if stats['updated'] % 50 == 0 and not dry_run:
                    db.commit()
                    logger.info(f"Committed {stats['updated']} updates...")
        
        except Exception as e:
            logger.error(f"Error processing {food_id}: {e}", exc_info=True)
            stats['errors'] += 1
            continue
    
    if not dry_run:
        db.commit()
    
    logger.info("")
    logger.info("=" * 70)
    logger.info("SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Total items in CSV: {stats['total_in_csv']}")
    logger.info(f"Foods found in database: {stats['foods_found']}")
    logger.info(f"Foods not found: {stats['foods_not_found']}")
    logger.info(f"Records updated: {stats['updated']}")
    logger.info(f"Skipped (already set): {stats['skipped_already_set']}")
    logger.info(f"Errors: {stats['errors']}")
    logger.info("=" * 70)
    
    return stats


def import_serving_info_to_food_kb(
    csv_file: Path,
    force_update: bool = False,
    dry_run: bool = False
) -> Dict[str, int]:
    """
    Main import function.
    
    Reads serving info CSV and updates kb_food_master.
    """
    # Read serving info CSV
    logger.info(f"Reading serving info from: {csv_file}")
    serving_info = read_serving_info_csv(csv_file)
    
    if not serving_info:
        logger.error("No serving information found in CSV file")
        return {'error': 'no_data'}
    
    logger.info(f"Found {len(serving_info)} food items with serving information")
    
    # Update database
    db = SessionLocal()
    try:
        stats = update_food_master_serving_info(db, serving_info, force_update, dry_run)
        return stats
    finally:
        db.close()


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Import serving information from CSV into kb_food_master'
    )
    parser.add_argument(
        '--csv-file',
        type=str,
        default='app/platform/knowledge_base/foods/food_serving_info.csv',
        help='Path to serving info CSV file'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run mode - do not commit to database'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force update even if values already exist'
    )
    
    args = parser.parse_args()
    
    # Resolve CSV file path
    backend_path = Path(__file__).parent.parent.parent.parent.parent
    csv_file = Path(args.csv_file)
    
    if not csv_file.is_absolute():
        csv_file = backend_path / csv_file
    
    if not csv_file.exists():
        logger.error(f"CSV file not found: {csv_file}")
        return 1
    
    if args.dry_run:
        logger.info("DRY RUN MODE - No changes will be saved to database")
    if args.force:
        logger.info("FORCE MODE - Will update even if values already exist")
    
    # Import data
    stats = import_serving_info_to_food_kb(csv_file, args.force, args.dry_run)
    
    if stats.get('errors', 0) > 0:
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

