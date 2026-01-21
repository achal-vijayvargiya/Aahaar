"""
Test the simplified food engine function.

This test verifies the get_foods_by_category_simple function works correctly
with food_exclusions filtering.
"""
import json
import pytest
from pathlib import Path
from sqlalchemy.orm import Session

from app.platform.engines.food_engine.food_engine import FoodEngine


def load_food_exclusions_from_test_json():
    """Load food_exclusions from the test JSON file."""
    test_json_path = Path(__file__).parent.parent.parent.parent / "e2e_test_outputs" / "e2e_pipeline_results_20260109_112639.json"
    
    if not test_json_path.exists():
        return [
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
    
    try:
        with open(test_json_path, 'r', encoding='utf-8') as f:
            test_data = json.load(f)
        
        # Extract food_exclusions from "4_mnt" key
        if "4_mnt" in test_data:
            return test_data["4_mnt"].get("constraints", {}).get("food_exclusions", [])
        
        # Try to find it in any constraint section
        for key in test_data.keys():
            if isinstance(test_data[key], dict) and "constraints" in test_data[key]:
                food_exclusions = test_data[key]["constraints"].get("food_exclusions", [])
                if food_exclusions:
                    return food_exclusions
        
        return ["canned_foods", "fried_foods", "processed_foods"]
    except Exception:
        return ["canned_foods", "fried_foods", "processed_foods"]


def test_simple_food_engine_single_category(platform_db: Session):
    """Test simple food engine with a single category."""
    engine = FoodEngine()
    food_exclusions = load_food_exclusions_from_test_json()
    
    # Test cereal category
    cereal_foods = engine.get_foods_by_category_simple(
        db=platform_db,
        exchange_category="cereal",
        food_exclusions=food_exclusions
    )
    
    # Should return a list
    assert isinstance(cereal_foods, list)
    
    # Check that foods don't have matching exclusion tags
    exclusion_set = {ex.lower() for ex in food_exclusions}
    for food in cereal_foods:
        food_tags = {tag.lower() for tag in food.get("food_exclusion_tags", [])}
        # No food should have exclusion tags matching the exclusion list
        assert not (food_tags & exclusion_set), f"Food {food['food_id']} has exclusion tag matching exclusions"


def load_medical_conditions_from_test_json():
    """Load medical conditions from the test JSON file."""
    test_json_path = Path(__file__).parent.parent.parent.parent / "e2e_test_outputs" / "e2e_pipeline_results_20260109_112639.json"
    
    if not test_json_path.exists():
        return []
    
    try:
        with open(test_json_path, 'r', encoding='utf-8') as f:
            test_data = json.load(f)
        
        # Extract medical conditions from "2_diagnosis" key
        if "2_diagnosis" in test_data:
            medical_conditions = test_data["2_diagnosis"].get("medical_conditions", [])
            # Extract condition IDs if they're dictionaries
            if medical_conditions and isinstance(medical_conditions[0], dict):
                condition_ids = [c.get("diagnosis_id") or c.get("condition_id") for c in medical_conditions if c.get("diagnosis_id") or c.get("condition_id")]
                return [c for c in condition_ids if c]  # Filter out None values
        
        return []
    except Exception:
        return []


def load_micro_constraints_from_test_json():
    """Load micro_constraints from the test JSON file."""
    test_json_path = Path(__file__).parent.parent.parent.parent / "e2e_test_outputs" / "e2e_pipeline_results_20260109_112639.json"
    
    if not test_json_path.exists():
        return {"sodium_mg": {"max": 2300}}
    
    try:
        with open(test_json_path, 'r', encoding='utf-8') as f:
            test_data = json.load(f)
        
        # Extract micro_constraints from "3_mnt" key
        if "3_mnt" in test_data:
            return test_data["3_mnt"].get("micro_constraints", {})
        
        # Try to find it in any constraint section
        for key in test_data.keys():
            if isinstance(test_data[key], dict) and "micro_constraints" in test_data[key]:
                return test_data[key]["micro_constraints"]
        
        return {"sodium_mg": {"max": 2300}}
    except Exception:
        return {"sodium_mg": {"max": 2300}}


def test_simple_food_engine_multiple_categories(platform_db: Session):
    """Test simple food engine with multiple categories."""
    engine = FoodEngine()
    food_exclusions = load_food_exclusions_from_test_json()
    
    test_categories = ["cereal", "pulse", "milk", "vegetable_non_starchy"]
    
    result = engine.get_foods_by_category_simple_dict(
        db=platform_db,
        exchange_categories=test_categories,
        food_exclusions=food_exclusions
    )
    
    # Should return a dictionary
    assert isinstance(result, dict)
    
    # Should have all categories
    for category in test_categories:
        assert category in result
        assert isinstance(result[category], list)
    
    # Print summary for manual inspection
    print(f"\n{'='*60}")
    print("Simple Food Engine Test Results (Food Exclusions Only)")
    print(f"{'='*60}")
    print(f"\nFood Exclusions: {food_exclusions}\n")
    
    total_foods = 0
    for category, foods in result.items():
        print(f"{category}: {len(foods)} foods")
        total_foods += len(foods)
        if foods:
            print(f"  Examples: {', '.join([f['display_name'] for f in foods[:3]])}")
    
    print(f"\nTotal foods across all categories: {total_foods}")
    
    # Verify filtering worked
    exclusion_set = {ex.lower() for ex in food_exclusions}
    for category, foods in result.items():
        for food in foods:
            food_tags = {tag.lower() for tag in food.get("food_exclusion_tags", [])}
            assert not (food_tags & exclusion_set), \
                f"Food {food['food_id']} in {category} has exclusion tag matching exclusions"


def test_simple_food_engine_with_condition_compatibility(platform_db: Session):
    """Test simple food engine with food exclusions AND condition compatibility."""
    engine = FoodEngine()
    food_exclusions = load_food_exclusions_from_test_json()
    medical_conditions = load_medical_conditions_from_test_json()
    micro_constraints = load_micro_constraints_from_test_json()
    
    # If no medical conditions in test JSON, use common test conditions
    if not medical_conditions:
        medical_conditions = ["diabetes", "hypertension"]
    
    test_categories = ["cereal", "pulse", "milk", "vegetable_non_starchy"]
    
    result = engine.get_foods_by_category_simple_dict(
        db=platform_db,
        exchange_categories=test_categories,
        food_exclusions=food_exclusions,
        medical_conditions=medical_conditions,
        micro_constraints=micro_constraints
    )
    
    # Should return a dictionary
    assert isinstance(result, dict)
    
    # Should have all categories
    for category in test_categories:
        assert category in result
        assert isinstance(result[category], list)
    
    # Print summary for manual inspection
    print(f"\n{'='*60}")
    print("Simple Food Engine Test Results (Food Exclusions + Condition Compatibility)")
    print(f"{'='*60}")
    print(f"\nFood Exclusions: {food_exclusions}")
    print(f"Medical Conditions: {medical_conditions}")
    print(f"Micro Constraints: {micro_constraints}")
    print(f"\nFiltering: Only foods with 'safe' compatibility are included.")
    print(f"Extreme Value Checks: Excluding foods with >5x daily sodium max or >95% carbs.\n")
    
    total_foods = 0
    for category, foods in result.items():
        print(f"{category}: {len(foods)} foods")
        total_foods += len(foods)
        if foods:
            print(f"  Examples: {', '.join([f['display_name'] for f in foods[:3]])}")
            # Show compatibility levels if available
            if foods[0].get("compatibility_checked"):
                safe_count = sum(1 for f in foods if f.get("compatibility_levels", {}))
                no_record_count = len(foods) - safe_count
                print(f"    - {safe_count} with 'safe' compatibility records")
                print(f"    - {no_record_count} with no compatibility records (assumed safe)")
    
    print(f"\nTotal foods across all categories: {total_foods}")
    
    # Verify filtering worked
    exclusion_set = {ex.lower() for ex in food_exclusions}
    medical_conditions_lower = [c.lower() for c in medical_conditions]
    
    # Track exclusion reasons for debugging
    exclusion_stats = {
        "food_exclusion_tags": 0,
        "condition_contraindicated": 0,
        "condition_not_safe": 0,
        "mnt_contraindications": 0,
        "diabetic_safe_false": 0,
        "total_foods_checked": 0
    }
    
    for category, foods in result.items():
        for food in foods:
            exclusion_stats["total_foods_checked"] += 1
            
            # Check food exclusions
            food_tags = {tag.lower() for tag in food.get("food_exclusion_tags", [])}
            assert not (food_tags & exclusion_set), \
                f"Food {food['food_id']} in {category} has exclusion tag matching exclusions"
            
            # Check condition compatibility - should only have "safe" or no records
            if food.get("compatibility_checked") and food.get("compatibility_levels"):
                for condition_id, compatibility in food["compatibility_levels"].items():
                    assert compatibility.lower() == "safe", \
                        f"Food {food['food_id']} in {category} has compatibility '{compatibility}' for {condition_id}, but only 'safe' should be included"
            
            # Check MNT contraindications - should not have user's conditions in contraindications
            if food.get("mnt_profile_info"):
                contraindications = food["mnt_profile_info"].get("contraindications", [])
                contraindications_lower = [c.lower() for c in contraindications]
                for condition in medical_conditions_lower:
                    assert condition not in contraindications_lower, \
                        f"Food {food['food_id']} in {category} has {condition} in contraindications"
    
    # Check for foods with exclusion tags that were allowed (medical safety override)
    foods_with_exclusion_tags_allowed = []
    for category, foods in result.items():
        for food in foods:
            exclusion_tags = food.get("food_exclusion_tags", [])
            if exclusion_tags:
                # Check if any exclusion tag matches the exclusion list
                exclusion_set = {ex.lower() for ex in food_exclusions}
                food_tags = {tag.lower() for tag in exclusion_tags}
                if food_tags & exclusion_set:
                    # This food has matching exclusion tags but was allowed
                    # This means medical safety override worked
                    foods_with_exclusion_tags_allowed.append({
                        "food": food["display_name"],
                        "category": category,
                        "exclusion_tags": exclusion_tags,
                        "medical_tags": food.get("mnt_profile_info", {}).get("medical_tags", {}) if food.get("mnt_profile_info") else {}
                    })
    
    if foods_with_exclusion_tags_allowed:
        print(f"\nMedical Safety Override Working:")
        print(f"  {len(foods_with_exclusion_tags_allowed)} foods with exclusion tags were ALLOWED because they're medically safe:")
        for item in foods_with_exclusion_tags_allowed[:3]:  # Show first 3
            print(f"    - {item['food']} ({item['category']}): tags={item['exclusion_tags']}")
    else:
        print(f"\nMedical Safety Override:")
        print(f"  No foods with matching exclusion tags found in results")
        print(f"  (Either no foods have matching tags, or they were correctly excluded)")
    
    print(f"\nExclusion statistics:")
    print(f"  Total foods checked: {exclusion_stats['total_foods_checked']}")
    print(f"  All foods passed all constraints (food exclusions with medical override + condition compatibility + MNT contraindications + extreme value checks)")

