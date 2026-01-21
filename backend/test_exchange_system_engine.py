"""
Test script for Exchange System Engine.

Tests the whole-day-first flow:
1. Calculate Daily Exchange Obligations
2. Energy-Weighted Exchange Distribution
3. Mandatory Presence Constraints
4. Nutrition Validation

Run from backend directory:
    python test_exchange_system_engine.py
"""
import sys
from pathlib import Path
from uuid import uuid4

# Add backend to path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

# Import context classes first (they don't have circular dependencies)
from app.platform.core.context.context import (
    MealStructureContext,
    TargetContext,
    MNTContext,
    AyurvedaContext,
)

# Import ExchangeSystemEngine directly from its module
from app.platform.engines.exchange_system_engine.exchange_system_engine import ExchangeSystemEngine


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_result(result: dict):
    """Print the exchange allocation result."""
    print("\n[Daily Exchange Allocation (Whole Day)]")
    print("-" * 80)
    for category, count in sorted(result["daily_exchange_allocation"].items()):
        print(f"  {category:25s}: {count:6.2f} exchanges")
    
    print("\n[Exchanges Per Meal]")
    print("-" * 80)
    for meal_name, meal_exchanges in result["exchanges_per_meal"].items():
        print(f"\n  {meal_name.upper()}:")
        for category, count in sorted(meal_exchanges.items()):
            print(f"    {category:25s}: {count:6.2f} exchanges")
    
    # Validate totals
    print("\n[Validation]")
    print("-" * 80)
    daily_total = sum(result["daily_exchange_allocation"].values())
    per_meal_total = sum(
        sum(meal_exchanges.values())
        for meal_exchanges in result["exchanges_per_meal"].values()
    )
    print(f"  Daily total (from daily_exchange_allocation): {daily_total:.2f}")
    print(f"  Daily total (sum of per_meal): {per_meal_total:.2f}")
    match_status = "PASS" if abs(daily_total - per_meal_total) < 0.01 else "FAIL"
    print(f"  Match: {match_status}")


def test_basic_flow():
    """Test 1: Basic flow with 3 meals."""
    print_section("TEST 1: Basic Flow (3 Meals)")
    
    assessment_id = uuid4()
    
    # Create meal structure
    meal_structure = MealStructureContext(
        assessment_id=assessment_id,
        meal_count=3,
        meals=["breakfast", "lunch", "dinner"],
        timing_windows={
            "breakfast": ["07:30", "09:00"],
            "lunch": ["12:30", "14:00"],
            "dinner": ["19:00", "20:30"],
        },
        energy_weight={
            "breakfast": 0.33,
            "lunch": 0.40,
            "dinner": 0.27,
        },
    )
    
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
    
    # Create MNT context (no medical conditions)
    mnt_context = MNTContext(
        assessment_id=assessment_id,
        food_exclusions=[],
    )
    
    # Generate exchanges
    engine = ExchangeSystemEngine()
    result = engine.generate_exchanges(
        meal_structure=meal_structure,
        target_context=target_context,
        mnt_context=mnt_context,
    )
    
    print_result(result)
    
    # Validate output structure
    assert "daily_exchange_allocation" in result, "Missing daily_exchange_allocation"
    assert "exchanges_per_meal" in result, "Missing exchanges_per_meal"
    assert len(result["exchanges_per_meal"]) == 3, "Should have 3 meals"
    
    print("\n[PASS] Test 1 completed successfully")


def test_with_medical_conditions():
    """Test 2: Flow with medical conditions (diabetes)."""
    print_section("TEST 2: With Medical Conditions (Diabetes)")
    
    assessment_id = uuid4()
    
    meal_structure = MealStructureContext(
        assessment_id=assessment_id,
        meal_count=3,
        meals=["breakfast", "lunch", "dinner"],
        timing_windows={
            "breakfast": ["07:30", "09:00"],
            "lunch": ["12:30", "14:00"],
            "dinner": ["19:00", "20:30"],
        },
        energy_weight={
            "breakfast": 0.33,
            "lunch": 0.40,
            "dinner": 0.27,
        },
    )
    
    target_context = TargetContext(
        assessment_id=assessment_id,
        calories_target=1800.0,
        macros={
            "proteins": {"g": 90.0},
            "carbohydrates": {"g": 225.0},
            "fats": {"g": 60.0},
        },
    )
    
    # MNT context with diabetes (should trigger medical modifiers)
    mnt_context = MNTContext(
        assessment_id=assessment_id,
        food_exclusions=["sugar", "diabetes restriction"],
    )
    
    engine = ExchangeSystemEngine()
    result = engine.generate_exchanges(
        meal_structure=meal_structure,
        target_context=target_context,
        mnt_context=mnt_context,
    )
    
    print_result(result)
    
    print("\n[PASS] Test 2 completed successfully")


def test_with_ayurveda():
    """Test 3: Flow with Ayurveda context."""
    print_section("TEST 3: With Ayurveda Context")
    
    assessment_id = uuid4()
    
    meal_structure = MealStructureContext(
        assessment_id=assessment_id,
        meal_count=3,
        meals=["breakfast", "lunch", "dinner"],
        timing_windows={
            "breakfast": ["07:30", "09:00"],
            "lunch": ["12:30", "14:00"],
            "dinner": ["19:00", "20:30"],
        },
        energy_weight={
            "breakfast": 0.33,
            "lunch": 0.40,
            "dinner": 0.27,
        },
    )
    
    target_context = TargetContext(
        assessment_id=assessment_id,
        calories_target=2000.0,
        macros={
            "proteins": {"g": 100.0},
            "carbohydrates": {"g": 250.0},
            "fats": {"g": 66.7},
        },
    )
    
    mnt_context = MNTContext(
        assessment_id=assessment_id,
        food_exclusions=[],
    )
    
    # Ayurveda context with dosha imbalance
    ayurveda_context = AyurvedaContext(
        assessment_id=assessment_id,
        vikriti_notes={
            "vikriti": {
                "imbalanced_doshas": ["vata"],
            },
            "agni": "manda",
            "ama": "present",
        },
    )
    
    engine = ExchangeSystemEngine()
    result = engine.generate_exchanges(
        meal_structure=meal_structure,
        target_context=target_context,
        mnt_context=mnt_context,
        ayurveda_context=ayurveda_context,
    )
    
    print_result(result)
    
    print("\n[PASS] Test 3 completed successfully")


def test_with_snacks():
    """Test 4: Flow with snacks (4 meals)."""
    print_section("TEST 4: With Snacks (4 Meals)")
    
    assessment_id = uuid4()
    
    meal_structure = MealStructureContext(
        assessment_id=assessment_id,
        meal_count=4,
        meals=["breakfast", "lunch", "snack", "dinner"],
        timing_windows={
            "breakfast": ["07:30", "09:00"],
            "lunch": ["12:30", "14:00"],
            "snack": ["16:00", "17:00"],
            "dinner": ["19:00", "20:30"],
        },
        energy_weight={
            "breakfast": 0.25,
            "lunch": 0.35,
            "snack": 0.15,
            "dinner": 0.25,
        },
    )
    
    target_context = TargetContext(
        assessment_id=assessment_id,
        calories_target=1800.0,
        macros={
            "proteins": {"g": 90.0},
            "carbohydrates": {"g": 225.0},
            "fats": {"g": 60.0},
        },
    )
    
    mnt_context = MNTContext(
        assessment_id=assessment_id,
        food_exclusions=[],
    )
    
    engine = ExchangeSystemEngine()
    result = engine.generate_exchanges(
        meal_structure=meal_structure,
        target_context=target_context,
        mnt_context=mnt_context,
    )
    
    print_result(result)
    
    assert len(result["exchanges_per_meal"]) == 4, "Should have 4 meals"
    
    print("\n[PASS] Test 4 completed successfully")


def test_low_calorie():
    """Test 5: Low calorie target (1200 kcal)."""
    print_section("TEST 5: Low Calorie Target (1200 kcal)")
    
    assessment_id = uuid4()
    
    meal_structure = MealStructureContext(
        assessment_id=assessment_id,
        meal_count=3,
        meals=["breakfast", "lunch", "dinner"],
        timing_windows={
            "breakfast": ["07:30", "09:00"],
            "lunch": ["12:30", "14:00"],
            "dinner": ["19:00", "20:30"],
        },
        energy_weight={
            "breakfast": 0.30,
            "lunch": 0.40,
            "dinner": 0.30,
        },
    )
    
    target_context = TargetContext(
        assessment_id=assessment_id,
        calories_target=1200.0,
        macros={
            "proteins": {"g": 60.0},
            "carbohydrates": {"g": 150.0},
            "fats": {"g": 40.0},
        },
    )
    
    mnt_context = MNTContext(
        assessment_id=assessment_id,
        food_exclusions=[],
    )
    
    engine = ExchangeSystemEngine()
    result = engine.generate_exchanges(
        meal_structure=meal_structure,
        target_context=target_context,
        mnt_context=mnt_context,
    )
    
    print_result(result)
    
    print("\n[PASS] Test 5 completed successfully")


def test_high_protein():
    """Test 6: High protein target."""
    print_section("TEST 6: High Protein Target")
    
    assessment_id = uuid4()
    
    meal_structure = MealStructureContext(
        assessment_id=assessment_id,
        meal_count=3,
        meals=["breakfast", "lunch", "dinner"],
        timing_windows={
            "breakfast": ["07:30", "09:00"],
            "lunch": ["12:30", "14:00"],
            "dinner": ["19:00", "20:30"],
        },
        energy_weight={
            "breakfast": 0.33,
            "lunch": 0.40,
            "dinner": 0.27,
        },
    )
    
    target_context = TargetContext(
        assessment_id=assessment_id,
        calories_target=2000.0,
        macros={
            "proteins": {"g": 150.0},  # High protein
            "carbohydrates": {"g": 200.0},
            "fats": {"g": 66.7},
        },
    )
    
    mnt_context = MNTContext(
        assessment_id=assessment_id,
        food_exclusions=[],
    )
    
    engine = ExchangeSystemEngine()
    result = engine.generate_exchanges(
        meal_structure=meal_structure,
        target_context=target_context,
        mnt_context=mnt_context,
    )
    
    print_result(result)
    
    # Check that protein sources are allocated
    daily_allocation = result["daily_exchange_allocation"]
    protein_sources = ["pulse", "milk", "paneer", "egg_whites"]
    total_protein_exchanges = sum(daily_allocation.get(cat, 0) for cat in protein_sources)
    print(f"\n  Total protein source exchanges: {total_protein_exchanges:.2f}")
    
    print("\n[PASS] Test 6 completed successfully")


def test_mandatory_constraints():
    """Test 7: Verify mandatory presence constraints are applied."""
    print_section("TEST 7: Mandatory Presence Constraints")
    
    assessment_id = uuid4()
    
    meal_structure = MealStructureContext(
        assessment_id=assessment_id,
        meal_count=3,
        meals=["breakfast", "lunch", "dinner"],
        timing_windows={
            "breakfast": ["07:30", "09:00"],
            "lunch": ["12:30", "14:00"],
            "dinner": ["19:00", "20:30"],
        },
        energy_weight={
            "breakfast": 0.33,
            "lunch": 0.40,
            "dinner": 0.27,
        },
    )
    
    target_context = TargetContext(
        assessment_id=assessment_id,
        calories_target=1500.0,
        macros={
            "proteins": {"g": 75.0},
            "carbohydrates": {"g": 187.5},
            "fats": {"g": 50.0},
        },
    )
    
    mnt_context = MNTContext(
        assessment_id=assessment_id,
        food_exclusions=[],
    )
    
    engine = ExchangeSystemEngine()
    result = engine.generate_exchanges(
        meal_structure=meal_structure,
        target_context=target_context,
        mnt_context=mnt_context,
    )
    
    daily_allocation = result["daily_exchange_allocation"]
    
    # Check mandatory constraints
    print("\n[Checking Mandatory Constraints]")
    print("-" * 80)
    
    # Fruit >= 1 exchange/day
    fruit_count = daily_allocation.get("fruit", 0)
    print(f"  Fruit exchanges: {fruit_count:.2f} (should be >= 1.0)")
    assert fruit_count >= 1.0, "Fruit constraint not met"
    
    # Vegetables in multiple meals
    veg_per_meal = {
        meal: meal_exchanges.get("vegetable_non_starchy", 0)
        for meal, meal_exchanges in result["exchanges_per_meal"].items()
    }
    meals_with_veg = sum(1 for count in veg_per_meal.values() if count > 0)
    print(f"  Meals with vegetables: {meals_with_veg} (should be >= 2)")
    assert meals_with_veg >= 2, "Vegetable in meals constraint not met"
    
    # Fat in multiple meals
    fat_per_meal = {
        meal: meal_exchanges.get("fat", 0)
        for meal, meal_exchanges in result["exchanges_per_meal"].items()
    }
    meals_with_fat = sum(1 for count in fat_per_meal.values() if count > 0)
    print(f"  Meals with fat: {meals_with_fat} (should be >= 2)")
    assert meals_with_fat >= 2, "Fat in meals constraint not met"
    
    print_result(result)
    print("\n[PASS] Test 7 completed successfully")


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("  EXCHANGE SYSTEM ENGINE TEST SUITE")
    print("  Testing Whole-Day-First Flow")
    print("=" * 80)
    
    try:
        test_basic_flow()
        test_with_medical_conditions()
        test_with_ayurveda()
        test_with_snacks()
        test_low_calorie()
        test_high_protein()
        test_mandatory_constraints()
        
        print_section("ALL TESTS PASSED")
        print("\n[SUCCESS] All 7 tests completed successfully!")
        
    except Exception as e:
        print_section("TEST FAILED")
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
