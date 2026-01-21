"""
Simplified version - Generate structured CSV file with serving information from exchange_info.txt.
"""

import sys
import csv
import re
from pathlib import Path
from typing import Dict, List, Optional
from difflib import SequenceMatcher

backend_dir = Path(__file__).parent.parent.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.utils.logger import logger


def normalize_food_name(name: str) -> str:
    """Normalize food name for matching."""
    if not name:
        return ""
    name = re.sub(r'\s*\([^)]*\)\s*', ' ', name).strip()
    name = name.lower()
    name = re.sub(r'[^\w\s]', ' ', name)
    name = re.sub(r'\s+', ' ', name)
    return name.strip()


def similarity_score(name1: str, name2: str) -> float:
    """Calculate similarity between two food names."""
    return SequenceMatcher(None, normalize_food_name(name1), normalize_food_name(name2)).ratio()


def build_food_id_mapping(csv_dir: Path) -> Dict[str, Dict[str, str]]:
    """Build mapping from food_id to food_name from CSV files."""
    mapping = {}
    csv_files = list(csv_dir.glob("*.csv"))
    
    for csv_file in csv_files:
        try:
            with open(csv_file, 'r', encoding='utf-8', errors='replace') as f:
                sample = f.read(1024)
                f.seek(0)
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter
                reader = csv.DictReader(f, delimiter=delimiter)
                fieldnames = [field.strip() for field in reader.fieldnames or []]
                reader.fieldnames = fieldnames
                
                for row in reader:
                    code = None
                    for col in ['Code', 'code', 'FOOD_CODE', 'food_code']:
                        if col in row and row[col]:
                            code = row[col].strip().upper()
                            break
                    if not code:
                        continue
                    
                    food_name = None
                    for col in ['Food Name', 'food name', 'food_name', 'FoodName', 'Name', 'name']:
                        if col in row and row[col]:
                            food_name = row[col].strip()
                            break
                    if not food_name:
                        continue
                    
                    exchange = None
                    for col in ['Exchange', 'exchange', 'Category', 'category']:
                        if col in row and row[col]:
                            exchange = row[col].strip()
                            break
                    
                    mapping[code] = {'name': food_name, 'category': exchange or ''}
        except Exception as e:
            logger.error(f"Error reading {csv_file}: {e}")
    
    return mapping


def parse_serving_unit(household_measure: str) -> Optional[str]:
    """Parse serving unit from household measure string."""
    if not household_measure or not household_measure.strip():
        return None
    
    measure = household_measure.strip().lower()
    
    if '/tsp' in measure or '/tbsp' in measure:
        return 'tsp' if 'tsp' in measure else 'tbsp'
    
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
    
    return None


def parse_exchange_info(exchange_file: Path) -> List[Dict[str, any]]:
    """Parse exchange_info.txt - simplified approach."""
    serving_data = []
    
    # Try multiple encoding methods
    try:
        with open(exchange_file, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        try:
            with open(exchange_file, 'r', encoding='utf-8-sig', errors='replace') as f:
                lines = f.readlines()
        except Exception as e2:
            logger.error(f"Error reading with utf-8-sig: {e2}")
            return serving_data
    
    # Strip newlines
    lines = [line.rstrip('\n\r') for line in lines]
    logger.info(f"Read {len(lines)} lines from exchange_info.txt")
    
    current_category = None
    category_map = {
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
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line or line.startswith('`'):
            continue
        
        line_upper = line.upper()
        parts = line.split('\t')
        
        # Debug first 20 lines
        if i < 20:
            logger.debug(f"Line {i+1}: {line[:60]} -> {len(parts)} parts, category={current_category}")
        
        # Check for category - must be standalone word/phrase
        for header, cat in category_map.items():
            first_part = parts[0].strip().upper() if parts else ""
            if header == first_part or (header in first_part and len(first_part) < 30):
                # Check if second part is empty or not a number
                is_category = True
                if len(parts) > 1:
                    second_part = parts[1].strip()
                    try:
                        float(second_part)
                        is_category = False  # Has number, so it's a data row
                    except ValueError:
                        pass  # Not a number, so it's a category header
                
                if is_category:
                    current_category = cat
                    logger.info(f"Category: {cat} at line {i+1}: {line[:50]}")
                    break
        
        # Skip headers (but allow data rows through)
        if any(x in line_upper for x in ['EXCHANGE LIST']):
            continue
        if any(x in line_upper for x in ['ITEMS', 'AMOUNT', 'ENERGY', 'DRY & FRESH']):
            # Check if it's actually a data row
            if len(parts) >= 2:
                try:
                    float(parts[1].strip())
                    # It's a data row, continue to parsing
                except (ValueError, IndexError):
                    continue  # It's a header, skip
            else:
                continue
        
        # Parse data rows
        if len(parts) >= 2 and current_category:
            food_name = parts[0].strip()
            if not food_name:
                continue
            
            # Skip category descriptions
            food_lower = food_name.lower()
            if any(x in food_lower for x in ['cereals (', 'pulses (', 'nuts &', 'veg a', 'veg b', 'veg c']):
                continue
            
            try:
                amount_str = parts[1].strip()
                
                if current_category == 'FRUITS':
                    serving_size_g = float(amount_str)
                    household = parts[2].strip() if len(parts) > 2 else ""
                    unit = parse_serving_unit(household) or "g"
                    serving_data.append({
                        'food_name': food_name,
                        'serving_size_g': serving_size_g,
                        'serving_unit': unit,
                        'category': current_category,
                        'household_measure': household
                    })
                elif current_category in ['FATS', 'SUGARS']:
                    if '/' in amount_str:
                        serving_size_g = float(amount_str.split('/')[0])
                        unit = parse_serving_unit(amount_str) or "tsp"
                    else:
                        serving_size_g = float(amount_str)
                        unit = "g"
                    serving_data.append({
                        'food_name': food_name,
                        'serving_size_g': serving_size_g,
                        'serving_unit': unit,
                        'category': current_category,
                        'household_measure': amount_str if '/' in amount_str else ""
                    })
                else:
                    serving_size_g = float(amount_str)
                    serving_data.append({
                        'food_name': food_name,
                        'serving_size_g': serving_size_g,
                        'serving_unit': "g",
                        'category': current_category,
                        'household_measure': ""
                    })
            except (ValueError, IndexError):
                pass
    
    return serving_data


def match_food_to_id(food_name: str, food_id_mapping: Dict[str, Dict[str, str]], 
                     category: Optional[str] = None, threshold: float = 0.6) -> Optional[str]:
    """Match food name to food_id using fuzzy matching."""
    best_match_id = None
    best_score = 0.0
    
    for food_id, food_info in food_id_mapping.items():
        if category:
            food_cat = food_info.get('category', '').upper()
            cat_mapping = {
                'CEREALS': 'CEREALS AND MILLETS',
                'PULSES': 'GRAIN LEGUMES',
                'NUTS_AND_OIL_SEEDS': 'NUTS AND OIL SEEDS',
                'FRUITS': 'FRUITS',
                'NONVEG': ['ANIMAL MEAT', 'POULTRY', 'MARINE FISH'],
            }
            expected_cats = cat_mapping.get(category, [])
            if isinstance(expected_cats, str):
                expected_cats = [expected_cats]
            if expected_cats and not any(ec in food_cat for ec in expected_cats):
                continue
        
        score = similarity_score(food_name, food_info.get('name', ''))
        if score > best_score and score >= threshold:
            best_score = score
            best_match_id = food_id
    
    return best_match_id


def main():
    script_dir = Path(__file__).parent
    exchange_file = script_dir / "exchange_info.txt"
    csv_dir = script_dir / "TableOneFormatedData"
    output_file = script_dir / "food_serving_info.csv"
    
    logger.info("Building food_id mapping...")
    food_id_mapping = build_food_id_mapping(csv_dir)
    logger.info(f"Found {len(food_id_mapping)} foods")
    
    logger.info("Parsing exchange_info.txt...")
    serving_data = parse_exchange_info(exchange_file)
    logger.info(f"Found {len(serving_data)} items")
    
    matched = []
    unmatched = []
    
    for item in serving_data:
        food_id = match_food_to_id(item['food_name'], food_id_mapping, item.get('category'))
        if food_id:
            matched.append({**item, 'food_id': food_id, 'match_score': 'matched'})
        else:
            unmatched.append({**item, 'food_id': '', 'match_score': 'UNMATCHED'})
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'food_id', 'food_name', 'serving_size_g', 'serving_unit', 
            'category', 'household_measure', 'match_score'
        ])
        writer.writeheader()
        writer.writerows(matched)
        writer.writerows(unmatched)
    
    logger.info(f"Matched: {len(matched)}, Unmatched: {len(unmatched)}")
    logger.info(f"Output: {output_file}")
    return 0 if len(unmatched) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

