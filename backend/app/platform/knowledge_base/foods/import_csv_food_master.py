"""
Import food master data from CSV files into kb_food_master table.

Part 1: Minimal import - only Code, Food Name, and Exchange fields.
Maps to: food_id, display_name, and category.

Usage:
    From backend directory:
    python -m app.platform.knowledge_base.foods.import_csv_food_master
    
    Or directly:
    python backend/app/platform/knowledge_base/foods/import_csv_food_master.py
"""

import sys
import csv
import argparse
from pathlib import Path
from typing import Dict, List, Optional

# Add backend directory to path
backend_dir = Path(__file__).parent.parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.database import SessionLocal
from app.platform.data.models.kb_food_master import KBFoodMaster
from app.utils.logger import logger


def normalize_food_name(name: str) -> str:
    """Clean and normalize food name from CSV."""
    if not name:
        return ""
    # Remove quotes and extra whitespace
    name = name.strip().strip('"').strip("'").strip()
    return name


def normalize_code(code: str) -> str:
    """Normalize code to uppercase for consistency."""
    if not code:
        return ""
    return code.strip().upper()


def normalize_category(exchange: str) -> Optional[str]:
    """
    Normalize Exchange column value to category.
    Converts to lowercase and replaces spaces with underscores.
    """
    if not exchange:
        return None
    # Convert to lowercase and replace spaces with underscores
    category = exchange.strip().lower().replace(" ", "_")
    return category if category else None


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
        logger.warning(f"Code column not found in row: {list(row.keys())}")
        return None
    
    if not name_key:
        logger.warning(f"Food Name column not found in row: {list(row.keys())}")
        return None
    
    code = normalize_code(row.get(code_key, ""))
    food_name = normalize_food_name(row.get(name_key, ""))
    exchange = row.get(exchange_key, "").strip() if exchange_key else ""
    
    if not code or not food_name:
        logger.debug(f"Skipping row with missing code or name: {row}")
        return None
    
    return {
        "code": code,
        "food_name": food_name,
        "exchange": exchange
    }


def process_csv_file(db: Session, file_path: Path, dry_run: bool = False) -> Dict[str, int]:
    """
    Process a single CSV file and insert data into kb_food_master.
    
    Returns stats dictionary with: processed, created, skipped, errors
    """
    stats = {"processed": 0, "created": 0, "skipped": 0, "errors": 0}
    
    logger.info(f"Processing file: {file_path.name}")
    
    try:
        rows = read_csv_file(file_path)
        logger.info(f"  Found {len(rows)} rows")
        
        for row in rows:
            try:
                # Extract data
                food_data = extract_food_data(row)
                if not food_data:
                    stats["skipped"] += 1
                    continue
                
                stats["processed"] += 1
                
                code = food_data["code"]
                food_name = food_data["food_name"]
                exchange = food_data["exchange"]
                
                # Normalize category
                category = normalize_category(exchange)
                
                if dry_run:
                    logger.info(f"  [DRY RUN] Would create: {code} - {food_name} (category: {category})")
                    stats["created"] += 1
                    continue
                
                # Check if food already exists
                existing = db.query(KBFoodMaster).filter(
                    KBFoodMaster.food_id == code
                ).first()
                
                if existing:
                    logger.debug(f"  Skipping existing food: {code}")
                    stats["skipped"] += 1
                    continue
                
                # Create food_master entry with minimal fields
                food_master = KBFoodMaster(
                    food_id=code,
                    display_name=food_name,
                    category=category
                )
                
                db.add(food_master)
                stats["created"] += 1
                
                # Commit in batches
                if stats["created"] % 50 == 0:
                    db.commit()
                    logger.info(f"  Committed {stats['created']} foods...")
            
            except IntegrityError as e:
                logger.warning(f"  Integrity error for row {row}: {e}")
                stats["errors"] += 1
                db.rollback()
                continue
            
            except Exception as e:
                logger.error(f"  Error processing row {row}: {e}", exc_info=True)
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


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Import food master data from CSV files (Part 1: Minimal fields)'
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
        help='Dry run mode - show what would be imported without saving'
    )
    parser.add_argument(
        '--files',
        nargs='+',
        help='Specific CSV files to process (if not provided, processes all CSV files)'
    )
    
    args = parser.parse_args()
    
    csv_dir = Path(args.csv_dir)
    if not csv_dir.exists():
        logger.error(f"CSV directory not found: {csv_dir}")
        return 1
    
    # Find CSV files
    if args.files:
        csv_files = [csv_dir / f for f in args.files if f.endswith('.csv')]
    else:
        csv_files = list(csv_dir.glob("*.csv"))
    
    if not csv_files:
        logger.warning(f"No CSV files found in {csv_dir}")
        return 1
    
    logger.info("=" * 70)
    logger.info("IMPORTING FOOD MASTER DATA FROM CSV FILES (PART 1: MINIMAL)")
    logger.info("=" * 70)
    logger.info(f"CSV Directory: {csv_dir}")
    logger.info(f"Found {len(csv_files)} CSV file(s)")
    logger.info(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    logger.info("Fields: Code -> food_id, Food Name -> display_name, Exchange -> category")
    logger.info("=" * 70)
    
    db = SessionLocal()
    try:
        total_stats = {"processed": 0, "created": 0, "skipped": 0, "errors": 0}
        
        for csv_file in sorted(csv_files):
            stats = process_csv_file(db, csv_file, dry_run=args.dry_run)
            for key in total_stats:
                total_stats[key] += stats[key]
            logger.info(
                f"  [OK] {csv_file.name}: "
                f"{stats['created']} created, "
                f"{stats['skipped']} skipped, "
                f"{stats['errors']} errors"
            )
        
        logger.info("=" * 70)
        logger.info("IMPORT SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Total processed: {total_stats['processed']}")
        logger.info(f"Total created: {total_stats['created']}")
        logger.info(f"Total skipped: {total_stats['skipped']}")
        logger.info(f"Total errors: {total_stats['errors']}")
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

