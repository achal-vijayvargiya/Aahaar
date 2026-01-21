"""
Simple test script for the simplified food engine function.

This script tests the get_foods_by_category_simple function with food_exclusions
from the e2e test output JSON file.

Usage:
    python -m app.platform.engines.food_engine.test_simple_food_engine
"""
import sys
import json
from pathlib import Path
from sqlalchemy.orm import Session

# Add backend to path if running directly
if __name__ == "__main__":
    backend_path = Path(__file__).parent.parent.parent.parent.parent
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))

# Import directly using importlib to avoid circular imports from __init__.py
import importlib.util
food_engine_path = Path(__file__).parent / "food_engine.py"
spec = importlib.util.spec_from_file_location("food_engine_module", food_engine_path)
food_engine_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(food_engine_module)
FoodEngine = food_engine_module.FoodEngine

# Import database session
from app.database import SessionLocal


def test_simple_food_engine():
    """Test the simple food engine function with food_exclusions from test JSON."""
    
    # Load food_exclusions from the test output JSON
    test_json_path = Path(__file__).parent.parent.parent.parent.parent / "e2e_test_outputs" / "e2e_pipeline_results_20260109_112639.json"
    
    if not test_json_path.exists():
        print(f"Test JSON file not found at: {test_json_path}")
        print("Using default food_exclusions for testing.")
        food_exclusions = [
            "canned_foods",
            "fried_foods",
            "full_fat_dairy",
            "high_gi_foods",
            "high_saturated_fat_foods",
            "high_sodium_foods",
            "pickled_foods",
            "processed_foods",
            "processed_meats",
            "refined_sugar",
            "salted_snacks",
            "sugar_sweetened_beverages",
            "trans_fats",
            "white_flour"
        ]
    else:
        try:
            with open(test_json_path, 'r', encoding='utf-8') as f:
                test_data = json.load(f)
            
            # Extract food_exclusions from the first assessment result
            # Look for "4_mnt" key which contains constraints
            if "4_mnt" in test_data:
                food_exclusions = test_data["4_mnt"].get("constraints", {}).get("food_exclusions", [])
            else:
                # Try to find it in any constraint section
                food_exclusions = []
                for key in test_data.keys():
                    if isinstance(test_data[key], dict) and "constraints" in test_data[key]:
                        food_exclusions = test_data[key]["constraints"].get("food_exclusions", [])
                        if food_exclusions:
                            break
                
                if not food_exclusions:
                    print("food_exclusions not found in test JSON, using defaults.")
                    food_exclusions = ["canned_foods", "fried_foods", "processed_foods"]
        except Exception as e:
            print(f"Error loading test JSON: {e}")
            print("Using default food_exclusions for testing.")
            food_exclusions = ["canned_foods", "fried_foods", "processed_foods"]
    
    print(f"\n{'='*60}")
    print("Testing Simple Food Engine with food_exclusions")
    print(f"{'='*60}")
    print(f"\nFood Exclusions: {food_exclusions}\n")
    
    # Initialize food engine
    engine = FoodEngine()
    
    # Get database session directly
    db: Session = SessionLocal()
    
    try:
        # Test categories from the exchange allocations in test JSON
        test_categories = ["cereal", "pulse", "milk", "vegetable_non_starchy"]
        
        print(f"Testing categories: {test_categories}\n")
        
        # Test single category
        print(f"{'─'*60}")
        print("Testing single category: 'cereal'")
        print(f"{'─'*60}")
        cereal_foods = engine.get_foods_by_category_simple(
            db=db,
            exchange_category="cereal",
            food_exclusions=food_exclusions
        )
        print(f"\nFound {len(cereal_foods)} cereal foods (after filtering by food_exclusions)")
        if cereal_foods:
            print("\nFirst 5 foods:")
            for i, food in enumerate(cereal_foods[:5], 1):
                print(f"  {i}. {food['display_name']} (ID: {food['food_id']})")
                print(f"     Exclusion tags: {food.get('food_exclusion_tags', [])}")
        
        # Test multiple categories
        print(f"\n{'─'*60}")
        print("Testing multiple categories")
        print(f"{'─'*60}")
        all_foods = engine.get_foods_by_category_simple_dict(
            db=db,
            exchange_categories=test_categories,
            food_exclusions=food_exclusions
        )
        
        print("\nResults by category:")
        for category, foods in all_foods.items():
            print(f"\n  {category}: {len(foods)} foods")
            if foods:
                print(f"    Examples: {', '.join([f['display_name'] for f in foods[:3]])}")
        
        # Summary
        print(f"\n{'='*60}")
        print("Summary")
        print(f"{'='*60}")
        total_foods = sum(len(foods) for foods in all_foods.values())
        print(f"Total foods found across all categories: {total_foods}")
        print(f"Categories tested: {len(all_foods)}")
        
        # Show exclusion statistics
        print(f"\nFood exclusion tags found in results:")
        all_exclusion_tags = set()
        for category_foods in all_foods.values():
            for food in category_foods:
                all_exclusion_tags.update(food.get('food_exclusion_tags', []))
        
        if all_exclusion_tags:
            print(f"  Unique exclusion tags in remaining foods: {sorted(all_exclusion_tags)}")
        else:
            print("  No exclusion tags found in remaining foods (good - all excluded foods filtered out)")
        
    finally:
        db.close()


if __name__ == "__main__":
    test_simple_food_engine()

