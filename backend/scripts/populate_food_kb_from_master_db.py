"""
Script to populate kb_food_master and related tables from Ahara Master Food Database.

This script:
1. Loads food names from ahara_food_list.json (the target list)
2. Matches them with foods in Ahara_Master_Food_Database_V1.0_770foods.json (data source)
3. Populates kb_food_master with actual data from the master database
4. Optionally populates related tables with nutrition data

Usage:
    python scripts/populate_food_kb_from_master_db.py
"""

import sys
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Set
from difflib import SequenceMatcher

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_
from app.database import SessionLocal
from app.platform.data.models.kb_food_master import KBFoodMaster
from app.platform.data.models.kb_food_nutrition_base import KBFoodNutritionBase
from app.platform.data.models.kb_food_exchange_profile import KBFoodExchangeProfile
from app.utils.logger import logger


# Category mapping from master DB categories to exchange categories
CATEGORY_MAPPING = {
    "Cereal": "cereal",
    "Pulse/Legume": "pulse",
    "Milk & Dairy": "milk",
    "Vegetable": "vegetable_non_starchy",  # Default, will be refined
    "Fruit": "fruit",
    "Nuts & Seeds": "nuts_seeds",
    "Fat & Oil": "fat",
    "Animal Proteins": None,  # Not in exchange system but we'll still add
    "Beverage": None,
    "Sweeteners": None,
    "Herbs & Spices": None,
    "Ayurvedic Medicinal Ingredients": None,
    "Fermented Foods": None,
    "Processed & Packaged Foods": None,
    "Global Functional": None,
}

# Map master DB categories to food_list categories for matching
MASTER_TO_FOOD_LIST_CATEGORY = {
    "Cereal": "Cereals & Millets",
    "Pulse/Legume": "Pulses & Legumes",
    "Milk & Dairy": "Milk & Dairy",
    "Vegetable": "Vegetables",
    "Fruit": "Fruits",
    "Nuts & Seeds": "Nuts & Seeds",
    "Fat & Oil": "Fats & Oils",
    "Animal Proteins": "Animal Proteins",
    "Beverage": "Beverages",
    "Herbs & Spices": "Herbs & Spices",
}

# Vegetable subcategory keywords
STARCHY_VEGETABLES = {"potato", "sweet potato", "yam", "taro", "arbi", "beetroot", "carrot"}


def normalize_food_name(name: str) -> str:
    """
    Normalize food name for matching.
    Removes extra spaces, converts to lowercase, removes special chars.
    """
    # Remove parenthetical cooking states/variations for matching
    name = re.sub(r'\s*\([^)]*\)\s*', ' ', name).strip()
    name = name.lower()
    name = re.sub(r'[^\w\s]', ' ', name)
    name = re.sub(r'\s+', ' ', name)
    return name.strip()


def similarity_score(name1: str, name2: str) -> float:
    """Calculate similarity between two food names."""
    norm1 = normalize_food_name(name1)
    norm2 = normalize_food_name(name2)
    return SequenceMatcher(None, norm1, norm2).ratio()


def find_best_match(target_name: str, master_db: List[Dict], category_filter: Optional[str] = None) -> Optional[Dict]:
    """
    Find best matching food in master database.
    Returns the master DB entry with highest similarity score.
    """
    best_match = None
    best_score = 0.0
    threshold = 0.6  # Minimum similarity threshold
    
    for food in master_db:
        master_name = food.get("Food Name", "")
        master_category = food.get("Category", "")
        
        # Category filtering
        if category_filter:
            expected_master_category = MASTER_TO_FOOD_LIST_CATEGORY.get(category_filter)
            if expected_master_category and master_category != expected_master_category:
                # Skip if category doesn't match (unless no category filter)
                continue
        
        score = similarity_score(target_name, master_name)
        
        if score > best_score and score >= threshold:
            best_score = score
            best_match = food
    
    return best_match


def generate_food_id(display_name: str) -> str:
    """Generate food_id from display_name."""
    cleaned = re.sub(r'\s*\([^)]*\)\s*', ' ', display_name)
    cleaned = cleaned.lower()
    cleaned = re.sub(r'[^\w]+', '_', cleaned)
    cleaned = cleaned.strip('_')
    cleaned = re.sub(r'_+', '_', cleaned)
    return cleaned


def extract_cooking_state(food_name: str) -> str:
    """Extract cooking state from food name."""
    if re.search(r'\b(raw|fresh|uncooked)\b', food_name, re.I):
        return 'raw'
    if re.search(r'\b(cooked|boiled|steamed|roasted|fried|grilled|baked)\b', food_name, re.I):
        return 'cooked'
    return 'raw'  # Default


def determine_exchange_category(master_category: str, food_name: str) -> Optional[str]:
    """Determine exchange category from master category and food name."""
    exchange_cat = CATEGORY_MAPPING.get(master_category)
    
    # Refine vegetable category
    if exchange_cat == "vegetable_non_starchy":
        food_lower = food_name.lower()
        if any(veg in food_lower for veg in STARCHY_VEGETABLES):
            return "vegetable_starchy"
    
    return exchange_cat


def parse_food_list(data: Dict) -> List[Tuple[str, str, Optional[str]]]:
    """
    Parse food list and return (food_name, category, subcategory) tuples.
    """
    foods = []
    
    for category_key, items in data.items():
        if category_key == "Vegetables" and isinstance(items, dict):
            for subcategory_key, subcategory_items in items.items():
                for food_name in subcategory_items:
                    foods.append((food_name, category_key, subcategory_key))
        elif isinstance(items, list):
            for food_name in items:
                foods.append((food_name, category_key, None))
    
    return foods


def create_food_master_entry(food_name: str, master_data: Dict, exchange_category: Optional[str]) -> Dict:
    """Create kb_food_master entry from master database data."""
    
    food_id = generate_food_id(food_name)
    master_category = master_data.get("Category", "")
    cooking_state = extract_cooking_state(food_name)
    region = master_data.get("Region", "pan_india")
    
    # Map region
    if "Indian" in region:
        region = "pan_india"
    elif "Global" in region:
        region = "global"
    else:
        region = "pan_india"  # Default
    
    # Determine diet_type
    if master_category == "Animal Proteins":
        diet_type = ["non_vegetarian"]
        food_type = "animal_protein"
    elif master_category == "Milk & Dairy":
        diet_type = ["vegetarian"]
        food_type = "dairy"
    else:
        diet_type = ["vegetarian", "vegan"]
        food_type_map = {
            "cereal": "grain",
            "pulse": "legume",
            "fruit": "fruit",
            "nuts_seeds": "nuts_seeds",
            "fat": "fat",
            "vegetable_non_starchy": "vegetable",
            "vegetable_starchy": "vegetable",
        }
        food_type = food_type_map.get(exchange_category, "other")
    
    # Determine serving info (defaults, should be refined based on actual data)
    serving_defaults = {
        "cereal": ("cup", 200.0),
        "pulse": ("cup", 200.0),
        "milk": ("cup", 250.0),
        "fruit": ("medium", 150.0),
        "nuts_seeds": ("tbsp", 15.0),
        "fat": ("tsp", 5.0),
        "vegetable_non_starchy": ("cup", 100.0),
        "vegetable_starchy": ("cup", 150.0),
    }
    serving_unit, serving_size_g = serving_defaults.get(exchange_category, (None, None))
    
    entry = {
        "food_id": food_id,
        "display_name": food_name,
        "aliases": None,  # Can be populated later
        "category": exchange_category,
        "food_type": food_type,
        "region": region,
        "diet_type": diet_type,
        "cooking_state": cooking_state,
        "common_serving_unit": serving_unit,
        "common_serving_size_g": serving_size_g,
        "version": "1.0",
        "status": "active",
        "source": "Ahara Master Food Database V1.0 / IFCT 2017",
        "source_reference": "Ahara_Master_Food_Database_V1.0_770foods.json",
        "last_reviewed": datetime.now(),
    }
    
    return entry


def create_nutrition_entry(food_id: str, master_data: Dict) -> Dict:
    """Create kb_food_nutrition_base entry from master database."""
    
    calories = master_data.get("Energy_kcal_per_100g")
    protein = master_data.get("Protein_g_per_100g", 0.0)
    fat = master_data.get("Fat_g_per_100g", 0.0)
    carbs = master_data.get("Carbs_g_per_100g", 0.0)
    
    # Calculate derived values
    calorie_density = calories / 100.0 if calories else None
    protein_density = (protein / calories * 100) if (calories and calories > 0) else None
    
    macros = {
        "protein_g": protein,
        "carbs_g": carbs,
        "fat_g": fat,
        "fiber_g": None,  # Not in master DB
        "sugar_g": None,
        "saturated_fat_g": None,
        "trans_fat_g": None,
        "added_sugar_g": None,
        "monounsaturated_fat_g": None,
        "polyunsaturated_fat_g": None,
        "omega_3_mg": None,
        "omega_6_mg": None,
    }
    
    micros = {
        "sodium_mg": None,
        "potassium_mg": None,
        "calcium_mg": None,
        "iron_mg": None,
        "magnesium_mg": None,
        "phosphorus_mg": None,
        "zinc_mg": None,
        "vitamin_c_mg": None,
        "vitamin_d_iu": None,
        "vitamin_e_mg": None,
        "vitamin_b12_mcg": None,
        "folate_mcg": None,
        "selenium_mcg": None,
        "iodine_mcg": None,
    }
    
    # Parse Key_Micronutrients if available (basic parsing)
    key_micros = master_data.get("Key_Micronutrients", "")
    # Could parse this more intelligently, but leaving as None for now
    
    entry = {
        "food_id": food_id,
        "calories_kcal": float(calories) if calories else None,
        "macros": macros,
        "micros": micros,
        "glycemic_properties": None,  # Not in master DB
        "calorie_density_kcal_per_g": float(calorie_density) if calorie_density else None,
        "protein_density_g_per_100kcal": float(protein_density) if protein_density else None,
    }
    
    return entry


def calculate_exchange_info(food_id: str, nutrition_data: Dict, exchange_category: Optional[str]) -> Optional[Dict]:
    """
    Calculate exchange profile based on nutrition data and category.
    Returns None if exchange_category is None (food doesn't fit exchange system).
    """
    if not exchange_category:
        return None
    
    # Standard exchange nutrition values (from exchange_category_definitions_kb.json)
    exchange_standards = {
        "cereal": {"calories": 80.0, "protein": 2.0, "carbs": 15.0},
        "pulse": {"calories": 100.0, "protein": 7.0, "carbs": 15.0},
        "milk": {"calories": 100.0, "protein": 6.0, "carbs": 10.0},
        "vegetable_non_starchy": {"calories": 25.0, "protein": 2.0, "carbs": 5.0},
        "vegetable_starchy": {"calories": 80.0, "protein": 2.0, "carbs": 18.0},
        "fruit": {"calories": 60.0, "protein": 1.0, "carbs": 15.0},
        "fat": {"calories": 45.0, "protein": 0.0, "carbs": 0.0},
        "nuts_seeds": {"calories": 70.0, "protein": 3.0, "carbs": 5.0},
    }
    
    standard = exchange_standards.get(exchange_category)
    if not standard:
        return None
    
    calories_per_100g = nutrition_data.get("calories_kcal")
    if not calories_per_100g:
        return None
    
    # Calculate serving size per exchange (g)
    # Based on calories: 1 exchange = standard_calories, so serving_size = (standard_calories / calories_per_100g) * 100
    serving_size_per_exchange_g = (standard["calories"] / calories_per_100g) * 100
    
    # Common serving size (default, should be refined)
    common_serving_defaults = {
        "cereal": 200.0,
        "pulse": 200.0,
        "milk": 250.0,
        "fruit": 150.0,
        "nuts_seeds": 15.0,
        "fat": 5.0,
        "vegetable_non_starchy": 100.0,
        "vegetable_starchy": 150.0,
    }
    common_serving_g = common_serving_defaults.get(exchange_category, 100.0)
    
    exchanges_per_common_serving = common_serving_g / serving_size_per_exchange_g
    
    return {
        "food_id": food_id,
        "exchange_category": exchange_category,
        "serving_size_per_exchange_g": round(serving_size_per_exchange_g, 2),
        "exchanges_per_common_serving": round(exchanges_per_common_serving, 2),
        "notes": f"1 exchange = {round(serving_size_per_exchange_g, 1)}g ≈ {standard['calories']} kcal",
    }


def populate_food_kb(db: Session, food_list_data: Dict, master_db_data: List[Dict]) -> Dict[str, int]:
    """
    Main population function.
    Returns stats: {created, matched, unmatched, errors}
    """
    stats = {"created": 0, "matched": 0, "unmatched": 0, "errors": 0}
    
    # Parse food list
    target_foods = parse_food_list(food_list_data)
    logger.info(f"Found {len(target_foods)} foods in target list")
    
    unmatched_foods = []
    
    for food_name, category, subcategory in target_foods:
        try:
            # Find match in master database
            master_match = find_best_match(food_name, master_db_data, category)
            
            if not master_match:
                unmatched_foods.append((food_name, category))
                stats["unmatched"] += 1
                logger.warning(f"No match found for: {food_name} ({category})")
                continue
            
            stats["matched"] += 1
            
            # Determine exchange category
            master_category = master_match.get("Category", "")
            exchange_category = determine_exchange_category(master_category, food_name)
            
            # Create food_master entry
            food_master_data = create_food_master_entry(food_name, master_match, exchange_category)
            food_id = food_master_data["food_id"]
            
            # Check if already exists
            existing = db.query(KBFoodMaster).filter(
                KBFoodMaster.food_id == food_id
            ).first()
            
            if existing:
                logger.debug(f"Skipping existing food: {food_id}")
                continue
            
            # Create KBFoodMaster
            food_master = KBFoodMaster(**food_master_data)
            db.add(food_master)
            
            # Create nutrition entry
            nutrition_data = create_nutrition_entry(food_id, master_match)
            if nutrition_data["calories_kcal"]:
                nutrition = KBFoodNutritionBase(**nutrition_data)
                db.add(nutrition)
            
            # Create exchange profile
            exchange_data = calculate_exchange_info(food_id, nutrition_data, exchange_category)
            if exchange_data:
                exchange_profile = KBFoodExchangeProfile(**exchange_data)
                db.add(exchange_profile)
            
            stats["created"] += 1
            
            # Commit in batches
            if stats["created"] % 50 == 0:
                db.commit()
                logger.info(f"Committed {stats['created']} foods...")
        
        except Exception as e:
            logger.error(f"Error processing {food_name}: {e}", exc_info=True)
            db.rollback()
            stats["errors"] += 1
            continue
    
    # Final commit
    db.commit()
    
    # Log unmatched foods
    if unmatched_foods:
        logger.warning(f"\n{len(unmatched_foods)} foods could not be matched:")
        for name, cat in unmatched_foods[:20]:  # Show first 20
            logger.warning(f"  - {name} ({cat})")
        if len(unmatched_foods) > 20:
            logger.warning(f"  ... and {len(unmatched_foods) - 20} more")
    
    return stats


def main():
    """Main function."""
    logger.info("=" * 70)
    logger.info("POPULATING KB_FOOD_MASTER FROM AHARA MASTER DATABASE")
    logger.info("=" * 70)
    
    # Load food list (target)
    food_list_path = Path(__file__).parent.parent / "Resource" / "Solution Docs" / "KB_Docs" / "vaish_ source" / "ahara_food_list.json"
    logger.info(f"Loading food list from: {food_list_path}")
    with open(food_list_path, 'r', encoding='utf-8') as f:
        food_list_data = json.load(f)
    
    # Load master database (data source)
    master_db_path = Path(__file__).parent.parent / "Resource" / "Ahara_Master_Food_Database_V1.0_770foods.json"
    logger.info(f"Loading master database from: {master_db_path}")
    with open(master_db_path, 'r', encoding='utf-8') as f:
        master_db_data = json.load(f)
    
    logger.info(f"Master database contains {len(master_db_data)} foods")
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Populate database
        stats = populate_food_kb(db, food_list_data, master_db_data)
        
        logger.info("=" * 70)
        logger.info("POPULATION COMPLETE!")
        logger.info(f"  Created: {stats['created']} foods")
        logger.info(f"  Matched: {stats['matched']} foods")
        logger.info(f"  Unmatched: {stats['unmatched']} foods")
        logger.info(f"  Errors: {stats['errors']} foods")
        logger.info("=" * 70)
        
        # Show summary by category
        from sqlalchemy import func
        category_counts = db.query(
            KBFoodMaster.category,
            func.count(KBFoodMaster.food_id).label('count')
        ).group_by(KBFoodMaster.category).all()
        
        logger.info("\nSummary by category:")
        for category, count in category_counts:
            logger.info(f"  {category or 'NULL'}: {count} foods")
    
    except Exception as e:
        logger.error(f"Error during population: {str(e)}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()





