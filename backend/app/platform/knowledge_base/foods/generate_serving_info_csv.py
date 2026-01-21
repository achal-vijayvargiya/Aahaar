"""
Generate structured CSV file with serving information from exchange_info.txt.

This script:
1. Reads all CSV files from TableOneFormatedData to build food_id → food_name mapping
2. Parses exchange_info.txt to extract serving information
3. Matches exchange list items to food_id using fuzzy matching
4. Outputs a structured CSV: food_serving_info.csv

Usage:
    python -m app.platform.knowledge_base.foods.generate_serving_info_csv
"""

import sys
import csv
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher

# Add backend directory to path
backend_dir = Path(__file__).parent.parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.utils.logger import logger


def normalize_food_name(name: str) -> str:
    """Normalize food name for matching."""
    if not name:
        return ""
    # Remove parenthetical information
    name = re.sub(r'\s*\([^)]*\)\s*', ' ', name).strip()
    name = name.lower()
    # Remove special characters but keep spaces
    name = re.sub(r'[^\w\s]', ' ', name)
    name = re.sub(r'\s+', ' ', name)
    return name.strip()


def similarity_score(name1: str, name2: str) -> float:
    """Calculate similarity between two food names."""
    norm1 = normalize_food_name(name1)
    norm2 = normalize_food_name(name2)
    return SequenceMatcher(None, norm1, norm2).ratio()


def build_food_id_mapping(csv_dir: Path) -> Dict[str, Dict[str, str]]:
    """
    Build mapping from food_id to food_name from CSV files.
    
    Returns: {food_id: {'name': food_name, 'category': category}}
    """
    mapping = {}
    csv_files = list(csv_dir.glob("*.csv"))
    
    for csv_file in csv_files:
        try:
            with open(csv_file, 'r', encoding='utf-8', errors='replace') as f:
                # Detect delimiter
                sample = f.read(1024)
                f.seek(0)
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter
                
                reader = csv.DictReader(f, delimiter=delimiter)
                fieldnames = [field.strip() for field in reader.fieldnames or []]
                reader.fieldnames = fieldnames
                
                for row in reader:
                    # Get code (food_id)
                    code = None
                    for col in ['Code', 'code', 'FOOD_CODE', 'food_code']:
                        if col in row and row[col]:
                            code = row[col].strip().upper()
                            break
                    
                    if not code:
                        continue
                    
                    # Get food name
                    food_name = None
                    for col in ['Food Name', 'food name', 'food_name', 'FoodName', 'Name', 'name']:
                        if col in row and row[col]:
                            food_name = row[col].strip()
                            break
                    
                    if not food_name:
                        continue
                    
                    # Get exchange category
                    exchange = None
                    for col in ['Exchange', 'exchange', 'Category', 'category']:
                        if col in row and row[col]:
                            exchange = row[col].strip()
                            break
                    
                    mapping[code] = {
                        'name': food_name,
                        'category': exchange or ''
                    }
        
        except Exception as e:
            logger.error(f"Error reading {csv_file}: {e}")
    
    return mapping


def parse_serving_unit(household_measure: str) -> Optional[str]:
    """
    Parse serving unit from household measure string.
    
    Examples:
        "1 small" -> "small"
        "1/3 cup" -> "cup"
        "2 pcs" -> "pieces"
        "1 med" -> "medium"
        "5/1tsp" -> "tsp"
    """
    if not household_measure or not household_measure.strip():
        return None
    
    measure = household_measure.strip().lower()
    
    # Handle tsp/tbsp format (e.g., "5/1tsp")
    if '/tsp' in measure or '/tbsp' in measure:
        if 'tbsp' in measure:
            return 'tbsp'
        return 'tsp'
    
    # Extract unit from common patterns
    unit_patterns = [
        (r'\d+\s*(?:small|sm)', 'small'),
        (r'\d+\s*(?:medium|med)', 'medium'),
        (r'\d+\s*(?:large|lg)', 'large'),
        (r'\d+\s*cup', 'cup'),
        (r'\d+\s*(?:pc|pcs|piece|pieces)', 'pieces'),
        (r'\d+\s*tsp', 'tsp'),
        (r'\d+\s*tbsp', 'tbsp'),
        (r'pellet', 'pellet'),
    ]
    
    for pattern, unit in unit_patterns:
        if re.search(pattern, measure):
            return unit
    
    # Default to "g" if no unit found
    return None


def parse_exchange_info(exchange_file: Path) -> List[Dict[str, any]]:
    """
    Parse exchange_info.txt and extract serving information.
    
    Returns list of dicts with: food_name, serving_size_g, serving_unit, category
    """
    serving_data = []
    
    with open(exchange_file, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
    
    current_category = None
    i = 0
    
    # Category headers mapping
    category_headers = {
        'CEREALS': 'CEREALS',
        'PULSES': 'PULSES',
        'NUTS & OILSEEDS': 'NUTS_AND_OIL_SEEDS',
        'FATS': 'FATS',
        'SUGARS': 'SUGARS',
        'MILK & MILK PRODUCTS': 'MILK',
        'VEGETABLES': 'VEGETABLES',
        'FRUITS': 'FRUITS',
        'NONVEG GROUP': 'NONVEG',
    }
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip empty lines, backticks, and section headers
        if not line or line.startswith('`'):
            i += 1
            continue
        
        # Detect category headers first (before other checks)
        category_found = False
        line_upper = line.upper()
        parts = line.split('\t')
        
        for header, category in category_headers.items():
            if header in line_upper:
                # Check if it's a standalone category header
                # Category headers are usually single words/phrases, possibly with empty trailing tabs
                first_part = parts[0].strip().upper() if parts else ""
                # Check if first part matches the header and second part is empty or doesn't contain numbers
                if header in first_part:
                    has_data = False
                    if len(parts) > 1:
                        try:
                            float(parts[1].strip())
                            has_data = True
                        except (ValueError, IndexError):
                            pass
                    
                    if not has_data:
                        current_category = category
                        category_found = True
                        logger.debug(f"Found category: {category} at line {i+1}: {line[:50]}")
                        i += 1
                        break
        
        if category_found:
            continue
        
        # Skip EXCHANGE LIST header
        if 'EXCHANGE LIST' in line_upper:
            i += 1
            continue
        
        # Skip header rows (but check if they have data)
        if any(x in line_upper for x in ['ITEMS', 'AMOUNT', 'ENERGY', 'CARBOHYDRATES', 'PROTEIN', 'FAT', 'HOUSEHOLD', 'MEASURES']):
            # Check if it's actually a data row (has numbers in second column)
            if len(parts) >= 2:
                try:
                    float(parts[1].strip())
                    # If successful, it's a data row, not a header - continue to parsing
                except (ValueError, IndexError):
                    i += 1
                    continue
            else:
                i += 1
                continue
        
        # Try to parse as data line
        parts = line.split('\t')
        
        if len(parts) >= 2 and current_category:
            food_name = parts[0].strip()
            
            # Skip empty food names
            if not food_name:
                i += 1
                continue
            
            # Skip header-like lines
            food_lower = food_name.lower()
            skip_keywords = ['items', 'amount', 'energy', 'carbohydrates', 'protein', 'fat', 'household', 'measures', 'dry & fresh fruits']
            if any(kw in food_lower for kw in skip_keywords):
                i += 1
                continue
            
            # Try to parse second column as number (serving size)
            try:
                amount_str = parts[1].strip()
                
                # Handle different formats
                if current_category == 'FRUITS':
                    # Fruits format: Food | Amount (gms) | Household Measures | Energy | ...
                    serving_size_g = float(amount_str)
                    household_measure = parts[2].strip() if len(parts) > 2 else ""
                    serving_unit = parse_serving_unit(household_measure) or "g"
                    
                    if serving_size_g > 0:
                        serving_data.append({
                            'food_name': food_name,
                            'serving_size_g': serving_size_g,
                            'serving_unit': serving_unit,
                            'category': current_category,
                            'household_measure': household_measure
                        })
                
                elif current_category in ['FATS', 'SUGARS']:
                    # Format: Item | Amount (like "5/1tsp") | Energy | ...
                    if '/' in amount_str:
                        serving_size_g = float(amount_str.split('/')[0].strip())
                        serving_unit = parse_serving_unit(amount_str) or "tsp"
                    else:
                        serving_size_g = float(amount_str)
                        serving_unit = "g"
                    
                    if serving_size_g > 0:
                        serving_data.append({
                            'food_name': food_name,
                            'serving_size_g': serving_size_g,
                            'serving_unit': serving_unit,
                            'category': current_category,
                            'household_measure': amount_str if '/' in amount_str else ""
                        })
                
                else:
                    # Standard format: Food | Amount (gms) | Energy | ...
                    serving_size_g = float(amount_str)
                    serving_unit = "g"  # Default to grams
                    
                    # Skip category description lines (they have numbers but are not individual foods)
                    if serving_size_g > 0:
                        # Skip lines that are clearly category descriptions
                        if not (food_lower.startswith('cereals') or food_lower.startswith('pulses') or 
                               food_lower.startswith('nuts') or food_lower.startswith('veg a') or
                               food_lower.startswith('veg b') or food_lower.startswith('veg c')):
                            serving_data.append({
                                'food_name': food_name,
                                'serving_size_g': serving_size_g,
                                'serving_unit': serving_unit,
                                'category': current_category,
                                'household_measure': ""
                            })
            
            except (ValueError, IndexError):
                # Not a data row, skip
                pass
        
        i += 1
    
    return serving_data


def match_food_to_id(food_name: str, food_id_mapping: Dict[str, Dict[str, str]], 
                     category: Optional[str] = None, threshold: float = 0.6) -> Optional[str]:
    """
    Match food name to food_id using fuzzy matching.
    
    Returns food_id if match found, None otherwise.
    """
    best_match_id = None
    best_score = 0.0
    
    normalized_target = normalize_food_name(food_name)
    
    for food_id, food_info in food_id_mapping.items():
        # Category filtering
        if category:
            food_cat = food_info.get('category', '').upper()
            cat_mapping = {
                'CEREALS': 'CEREALS AND MILLETS',
                'PULSES': 'GRAIN LEGUMES',
                'NUTS_AND_OIL_SEEDS': 'NUTS AND OIL SEEDS',
                'FATS': 'FATS',
                'SUGARS': 'SUGARS',
                'MILK': 'MILK',
                'VEGETABLES': ['GREEN LEAFY VEGETABLES', 'OTHER VEGETABLES', 'ROOTS AND TUBERS'],
                'FRUITS': 'FRUITS',
                'NONVEG': ['ANIMAL MEAT', 'POULTRY', 'MARINE FISH'],
            }
            
            expected_cats = cat_mapping.get(category, [])
            if isinstance(expected_cats, str):
                expected_cats = [expected_cats]
            
            if expected_cats and not any(ec in food_cat for ec in expected_cats):
                continue
        
        food_name_db = food_info.get('name', '')
        score = similarity_score(food_name, food_name_db)
        
        if score > best_score and score >= threshold:
            best_score = score
            best_match_id = food_id
    
    return best_match_id


def generate_serving_info_csv(
    exchange_file: Path,
    csv_dir: Path,
    output_file: Path
) -> Dict[str, int]:
    """
    Generate structured CSV with serving information.
    
    Returns statistics dictionary.
    """
    stats = {
        'total_exchange_items': 0,
        'matched': 0,
        'unmatched': 0,
        'output_rows': 0
    }
    
    logger.info("=" * 70)
    logger.info("GENERATING SERVING INFO CSV")
    logger.info("=" * 70)
    
    # Build food_id mapping
    logger.info("Building food_id mapping from CSV files...")
    food_id_mapping = build_food_id_mapping(csv_dir)
    logger.info(f"Found {len(food_id_mapping)} foods in CSV files")
    
    # Parse exchange info
    logger.info("Parsing exchange_info.txt...")
    serving_data = parse_exchange_info(exchange_file)
    stats['total_exchange_items'] = len(serving_data)
    logger.info(f"Found {len(serving_data)} items in exchange list")
    
    if len(serving_data) == 0:
        logger.warning("No items parsed! Checking file format...")
        # Debug: show first few lines
        with open(exchange_file, 'r', encoding='utf-8', errors='replace') as f:
            debug_lines = f.readlines()[:20]
            logger.info("First 20 lines of exchange_info.txt:")
            for idx, line in enumerate(debug_lines, 1):
                parts = line.strip().split('\t')
                logger.info(f"  {idx}: {repr(line[:80])} -> {len(parts)} parts, first: {parts[0][:30] if parts else 'N/A'}")
    
    # Match and generate CSV
    logger.info("Matching foods and generating CSV...")
    
    matched_items = []
    unmatched_items = []
    
    for item in serving_data:
        food_name = item['food_name']
        category = item.get('category')
        
        food_id = match_food_to_id(food_name, food_id_mapping, category)
        
        if food_id:
            matched_items.append({
                'food_id': food_id,
                'food_name': food_name,
                'serving_size_g': item['serving_size_g'],
                'serving_unit': item['serving_unit'],
                'category': category or '',
                'household_measure': item.get('household_measure', ''),
                'match_score': 'matched'
            })
            stats['matched'] += 1
        else:
            unmatched_items.append({
                'food_id': '',
                'food_name': food_name,
                'serving_size_g': item['serving_size_g'],
                'serving_unit': item['serving_unit'],
                'category': category or '',
                'household_measure': item.get('household_measure', ''),
                'match_score': 'UNMATCHED'
            })
            stats['unmatched'] += 1
    
    # Write CSV file (matched first, then unmatched for review)
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'food_id', 'food_name', 'serving_size_g', 'serving_unit', 
            'category', 'household_measure', 'match_score'
        ])
        writer.writeheader()
        
        # Write matched items
        for item in matched_items:
            writer.writerow(item)
            stats['output_rows'] += 1
        
        # Write unmatched items (for manual review)
        for item in unmatched_items:
            writer.writerow(item)
            stats['output_rows'] += 1
    
    logger.info("=" * 70)
    logger.info("SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Total exchange items: {stats['total_exchange_items']}")
    logger.info(f"Matched: {stats['matched']}")
    logger.info(f"Unmatched: {stats['unmatched']}")
    logger.info(f"Output CSV: {output_file}")
    logger.info("=" * 70)
    
    if stats['unmatched'] > 0:
        logger.warning(f"\n{stats['unmatched']} items could not be matched automatically.")
        logger.warning("Please review the CSV file and manually add food_id for unmatched items.")
    
    return stats


def main():
    """Main function."""
    # Paths
    script_dir = Path(__file__).parent
    exchange_file = script_dir / "exchange_info.txt"
    csv_dir = script_dir / "TableOneFormatedData"
    output_file = script_dir / "food_serving_info.csv"
    
    if not exchange_file.exists():
        logger.error(f"Exchange info file not found: {exchange_file}")
        return 1
    
    if not csv_dir.exists():
        logger.error(f"CSV directory not found: {csv_dir}")
        return 1
    
    stats = generate_serving_info_csv(exchange_file, csv_dir, output_file)
    
    if stats['unmatched'] > 0:
        return 1  # Return error code if there are unmatched items
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

