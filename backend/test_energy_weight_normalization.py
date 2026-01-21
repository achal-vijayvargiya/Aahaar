"""
Test script to verify energy_weight normalization.

Tests that energy_weight values:
1. Are rounded to 2 decimal places
2. Sum exactly to 1.0
3. Are normalized proportionally if needed
4. Don't change meal count or ordering
"""
import sys
from pathlib import Path
from uuid import uuid4

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

# Import context classes first (they don't have circular dependencies)
from app.platform.core.context.context import TargetContext

# Import MealStructureEngine directly from its module
from app.platform.engines.meal_structure_engine.meal_structure_engine import MealStructureEngine


def test_energy_weight_normalization():
    """Test that energy_weight is properly normalized."""
    print("=" * 80)
    print("Testing Energy Weight Normalization")
    print("=" * 80)
    
    assessment_id = uuid4()
    
    # Create target context
    target_context = TargetContext(
        assessment_id=assessment_id,
        calories_target=1500.0,
        macros={
            "proteins": {"g": 75.0},
            "carbohydrates": {"g": 187.5},
            "fats": {"g": 50.0},
        },
    )
    
    # Create assessment snapshot
    assessment_snapshot = {
        "client_context": {
            "age": 35,
            "gender": "male",
            "height_cm": 170,
            "weight_kg": 75,
            "activity_level": "moderately_active",
            "wake_time": "07:00",
            "sleep_time": "22:00",
        },
        "goals": {
            "primary_goal": "maintenance",
        },
    }
    
    # Generate meal structure
    engine = MealStructureEngine()
    meal_structure = engine.generate_structure(
        target_context=target_context,
        assessment_snapshot=assessment_snapshot,
    )
    
    # Verify energy_weight properties
    energy_weight = meal_structure.energy_weight
    meals = meal_structure.meals
    
    print(f"\nMeal Count: {meal_structure.meal_count}")
    print(f"Meals: {meals}")
    print(f"\nEnergy Weights:")
    print("-" * 80)
    
    total = 0.0
    for meal_name in meals:
        weight = energy_weight.get(meal_name, 0)
        total += weight
        print(f"  {meal_name:20s}: {weight:6.2f}")
    
    print("-" * 80)
    print(f"  {'Total':20s}: {total:6.2f}")
    
    # Verify properties
    print("\n[Validation]")
    print("-" * 80)
    
    # 1. Check all values are rounded to 2 decimal places
    all_rounded = all(
        round(weight, 2) == weight for weight in energy_weight.values()
    )
    print(f"  All values rounded to 2 decimals: {'PASS' if all_rounded else 'FAIL'}")
    
    # 2. Check sum is exactly 1.0
    sum_exact = abs(total - 1.0) < 0.0001
    print(f"  Sum equals 1.0 exactly: {'PASS' if sum_exact else f'FAIL (got {total:.6f})'}")
    
    # 3. Check all meals have weights
    all_meals_have_weights = all(
        meal_name in energy_weight for meal_name in meals
    )
    print(f"  All meals have weights: {'PASS' if all_meals_have_weights else 'FAIL'}")
    
    # 4. Check meal count matches
    meal_count_match = len(meals) == meal_structure.meal_count
    print(f"  Meal count matches: {'PASS' if meal_count_match else 'FAIL'}")
    
    # 5. Check all weights are positive
    all_positive = all(weight > 0 for weight in energy_weight.values())
    print(f"  All weights positive: {'PASS' if all_positive else 'FAIL'}")
    
    if all_rounded and sum_exact and all_meals_have_weights and meal_count_match and all_positive:
        print("\n[SUCCESS] All validation checks passed!")
        return True
    else:
        print("\n[FAILURE] Some validation checks failed!")
        return False


if __name__ == "__main__":
    try:
        success = test_energy_weight_normalization()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
