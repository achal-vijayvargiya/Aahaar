"""
Unit tests for MealAllocationEngine and MealAllocator.

Tests deterministic food allocation across 7 days, variety enforcement,
nutrition totals, and edge case handling.

Pure unit tests — no DB required. All inputs are built from plain dicts/dataclasses.
"""
import pytest
from uuid import uuid4
from datetime import datetime
from typing import Dict, List, Any

from app.platform.engines.recipe_engine.meal_allocation_engine import MealAllocationEngine
from app.platform.engines.recipe_engine.meal_allocator import MealAllocator
from app.platform.engines.recipe_engine.variety_tracker import VarietyTracker
from app.platform.core.context import ExchangeContext, MealStructureContext


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------

def make_exchange_context(exchanges_per_meal=None, per_meal_targets=None):
    return ExchangeContext(
        assessment_id=uuid4(),
        exchanges_per_meal=exchanges_per_meal or {
            "breakfast": {"cereal": 2, "milk": 1},
            "lunch": {"cereal": 3, "pulse": 1, "vegetable": 1},
            "dinner": {"cereal": 2, "pulse": 1, "vegetable": 1},
        },
        per_meal_targets=per_meal_targets or {
            "breakfast": {"calories": 450, "protein_g": 18, "carbs_g": 60, "fat_g": 15},
            "lunch": {"calories": 650, "protein_g": 26, "carbs_g": 85, "fat_g": 20},
            "dinner": {"calories": 550, "protein_g": 22, "carbs_g": 70, "fat_g": 18},
        },
    )


def make_meal_structure(meals=None):
    meals = meals or ["breakfast", "lunch", "dinner"]
    weights = {m: 1.0 / len(meals) for m in meals}
    return MealStructureContext(
        assessment_id=uuid4(),
        meal_count=len(meals),
        meals=meals,
        timing_windows={},
        energy_weight=weights,
    )


def make_food(food_id, display_name=None, serving_size_g=30.0, calories=350.0,
              protein_g=10.0, carbs_g=65.0, fat_g=3.0, fiber_g=3.0):
    return {
        "food_id": food_id,
        "display_name": display_name or food_id.replace("_", " ").title(),
        "exchange_category": "cereal",
        "serving_size_per_exchange_g": serving_size_g,
        "food_type": "grain",
        "cooking_state": "raw",
        "nutrition": {
            "calories": calories,
            "macros": {
                "protein_g": protein_g,
                "carbs_g": carbs_g,
                "fat_g": fat_g,
                "fiber_g": fiber_g,
            },
            "micros": {},
        },
    }


def make_food_engine_output(num_foods_per_category=10):
    """Build a realistic food_engine_output with enough food variety for 7 days."""
    cereal_foods = [make_food(f"cereal_{i}", calories=350 + i * 5) for i in range(num_foods_per_category)]
    pulse_foods = [make_food(f"pulse_{i}", calories=300 + i * 5,
                             protein_g=20.0, carbs_g=50.0) for i in range(num_foods_per_category)]
    milk_foods = [make_food(f"milk_{i}", calories=60 + i * 5,
                            protein_g=3.0, carbs_g=5.0, fat_g=3.0) for i in range(num_foods_per_category)]
    vegetable_foods = [make_food(f"veg_{i}", calories=25 + i * 2,
                                 carbs_g=5.0, fiber_g=2.0, protein_g=2.0) for i in range(num_foods_per_category)]

    for lst in (cereal_foods, pulse_foods, milk_foods, vegetable_foods):
        for i, food in enumerate(lst):
            food["ranking"] = {"rank": i + 1, "total_score": 100.0 - i}

    return {
        "category_wise_foods": {
            "cereal": cereal_foods,
            "pulse": pulse_foods,
            "milk": milk_foods,
            "vegetable": vegetable_foods,
        }
    }


# ---------------------------------------------------------------------------
# TestMealAllocationEngine — 7-day plan generation
# ---------------------------------------------------------------------------

class TestMealAllocationEngine:

    def setup_method(self):
        self.engine = MealAllocationEngine()
        self.exchange_ctx = make_exchange_context()
        self.meal_structure = make_meal_structure()
        self.food_output = make_food_engine_output(num_foods_per_category=10)

    def test_seven_day_plan_has_seven_days(self):
        result = self.engine.allocate_meal_plan(
            exchange_context=self.exchange_ctx,
            meal_structure=self.meal_structure,
            food_engine_output=self.food_output,
            num_days=7,
        )
        assert result["plan_duration_days"] == 7
        assert len(result["days"]) == 7

    def test_day_keys_are_sequential(self):
        result = self.engine.allocate_meal_plan(
            exchange_context=self.exchange_ctx,
            meal_structure=self.meal_structure,
            food_engine_output=self.food_output,
            num_days=7,
        )
        expected_keys = {f"day_{i}" for i in range(1, 8)}
        assert set(result["days"].keys()) == expected_keys

    def test_each_day_has_all_meals(self):
        result = self.engine.allocate_meal_plan(
            exchange_context=self.exchange_ctx,
            meal_structure=self.meal_structure,
            food_engine_output=self.food_output,
            num_days=7,
        )
        for day_key, day_data in result["days"].items():
            meals = day_data["meals"]
            assert "breakfast" in meals, f"{day_key} missing breakfast"
            assert "lunch" in meals, f"{day_key} missing lunch"
            assert "dinner" in meals, f"{day_key} missing dinner"

    def test_each_meal_has_allocated_foods(self):
        result = self.engine.allocate_meal_plan(
            exchange_context=self.exchange_ctx,
            meal_structure=self.meal_structure,
            food_engine_output=self.food_output,
            num_days=7,
        )
        for day_data in result["days"].values():
            for meal_name, meal_data in day_data["meals"].items():
                foods = meal_data["allocated_foods"]
                assert len(foods) > 0, f"{meal_name} has no allocated foods"

    def test_allocated_food_has_required_fields(self):
        result = self.engine.allocate_meal_plan(
            exchange_context=self.exchange_ctx,
            meal_structure=self.meal_structure,
            food_engine_output=self.food_output,
            num_days=1,
        )
        day = result["days"]["day_1"]
        food = day["meals"]["breakfast"]["allocated_foods"][0]
        assert "food_id" in food
        assert "display_name" in food
        assert "exchange_category" in food
        assert "exchanges" in food
        assert "quantity_g" in food
        assert "nutrition" in food

    def test_quantity_g_is_positive(self):
        result = self.engine.allocate_meal_plan(
            exchange_context=self.exchange_ctx,
            meal_structure=self.meal_structure,
            food_engine_output=self.food_output,
            num_days=1,
        )
        for meal_data in result["days"]["day_1"]["meals"].values():
            for food in meal_data["allocated_foods"]:
                assert food["quantity_g"] > 0, f"{food['food_id']} has zero quantity"

    def test_daily_totals_are_positive_numbers(self):
        result = self.engine.allocate_meal_plan(
            exchange_context=self.exchange_ctx,
            meal_structure=self.meal_structure,
            food_engine_output=self.food_output,
            num_days=7,
        )
        for day_key, day_data in result["days"].items():
            totals = day_data["daily_totals"]
            assert "calories" in totals
            assert totals["calories"] > 0, f"{day_key} has 0 calories"

    def test_variety_metrics_key_present(self):
        result = self.engine.allocate_meal_plan(
            exchange_context=self.exchange_ctx,
            meal_structure=self.meal_structure,
            food_engine_output=self.food_output,
            num_days=7,
        )
        assert "variety_metrics" in result

    def test_nutrition_summary_key_present(self):
        result = self.engine.allocate_meal_plan(
            exchange_context=self.exchange_ctx,
            meal_structure=self.meal_structure,
            food_engine_output=self.food_output,
            num_days=7,
        )
        assert "nutrition_summary" in result
        assert "average_daily" in result["nutrition_summary"]

    def test_start_date_recorded(self):
        start = datetime(2025, 1, 15)
        result = self.engine.allocate_meal_plan(
            exchange_context=self.exchange_ctx,
            meal_structure=self.meal_structure,
            food_engine_output=self.food_output,
            num_days=7,
            start_date=start,
        )
        assert result["start_date"].startswith("2025-01-15")

    def test_single_day_plan(self):
        result = self.engine.allocate_meal_plan(
            exchange_context=self.exchange_ctx,
            meal_structure=self.meal_structure,
            food_engine_output=self.food_output,
            num_days=1,
        )
        assert result["plan_duration_days"] == 1
        assert len(result["days"]) == 1


class TestMealAllocationEngineVariety:

    def setup_method(self):
        self.engine = MealAllocationEngine()
        self.exchange_ctx = make_exchange_context()
        self.meal_structure = make_meal_structure()
        self.food_output = make_food_engine_output(num_foods_per_category=10)

    def test_rule_a_no_same_day_repeats(self):
        """No food should repeat within the same day across different meals."""
        result = self.engine.allocate_meal_plan(
            exchange_context=self.exchange_ctx,
            meal_structure=self.meal_structure,
            food_engine_output=self.food_output,
            num_days=7,
        )
        violations = result["variety_metrics"]["rule_violations"]["same_day_variety"]
        assert violations == [], f"Rule A violations found: {violations}"

    def test_rule_a_violations_are_zero(self):
        """Rule A (same-day variety) is actively enforced at selection time — must be zero violations."""
        result = self.engine.allocate_meal_plan(
            exchange_context=self.exchange_ctx,
            meal_structure=self.meal_structure,
            food_engine_output=self.food_output,
            num_days=7,
        )
        violations = result["variety_metrics"]["rule_violations"]["same_day_variety"]
        assert violations == [], f"Rule A violations found: {violations}"

    def test_variety_metrics_reports_rule_b_violations(self):
        """Rule B (cross-day combination) is tracked in metrics even if not always preventable.
        The engine warns about violations but does not yet backtrack to resolve them.
        """
        result = self.engine.allocate_meal_plan(
            exchange_context=self.exchange_ctx,
            meal_structure=self.meal_structure,
            food_engine_output=self.food_output,
            num_days=7,
        )
        metrics = result["variety_metrics"]
        # The field must exist whether violations occurred or not
        assert "rule_violations" in metrics
        assert "cross_day_combination" in metrics["rule_violations"]

    def test_unique_foods_increase_with_more_variety(self):
        """7-day plan should have more unique foods than a 1-day plan."""
        result_7 = self.engine.allocate_meal_plan(
            exchange_context=self.exchange_ctx,
            meal_structure=self.meal_structure,
            food_engine_output=self.food_output,
            num_days=7,
        )
        result_1 = self.engine.allocate_meal_plan(
            exchange_context=self.exchange_ctx,
            meal_structure=self.meal_structure,
            food_engine_output=self.food_output,
            num_days=1,
        )
        total_7 = result_7["variety_metrics"]["total_unique_foods"]
        total_1 = result_1["variety_metrics"]["total_unique_foods"]
        assert total_7 >= total_1

    def test_missing_exchange_category_produces_warning_not_crash(self):
        """If a required exchange category has no foods, allocator should warn, not crash."""
        incomplete_output = {
            "category_wise_foods": {
                "cereal": make_food_engine_output()["category_wise_foods"]["cereal"],
                # "pulse" intentionally missing
                "milk": make_food_engine_output()["category_wise_foods"]["milk"],
                "vegetable": make_food_engine_output()["category_wise_foods"]["vegetable"],
            }
        }
        result = self.engine.allocate_meal_plan(
            exchange_context=self.exchange_ctx,
            meal_structure=self.meal_structure,
            food_engine_output=incomplete_output,
            num_days=1,
        )
        # Should complete without raising
        assert "days" in result
        # Warning should be recorded in the meal validation
        warnings_found = False
        for meal_data in result["days"]["day_1"]["meals"].values():
            if meal_data["validation"]["warnings"]:
                warnings_found = True
                break
        assert warnings_found, "Expected a warning for missing 'pulse' category"

    def test_empty_food_lists_handled_gracefully(self):
        """Completely empty food_engine_output should not crash."""
        empty_output = {"category_wise_foods": {}}
        result = self.engine.allocate_meal_plan(
            exchange_context=self.exchange_ctx,
            meal_structure=self.meal_structure,
            food_engine_output=empty_output,
            num_days=1,
        )
        assert "days" in result


# ---------------------------------------------------------------------------
# TestMealAllocator — single meal allocation
# ---------------------------------------------------------------------------

class TestMealAllocator:

    def setup_method(self):
        self.tracker = VarietyTracker()
        self.allocator = MealAllocator(variety_tracker=self.tracker)

    def _make_ranked_foods(self, category="cereal", n=5):
        return {
            category: [
                {
                    "food_id": f"{category}_{i}",
                    "display_name": f"{category.title()} {i}",
                    "exchange_category": category,
                    "serving_size_per_exchange_g": 30.0,
                    "nutrition": {
                        "calories": 350.0,
                        "macros": {"protein_g": 10.0, "carbs_g": 65.0, "fat_g": 3.0, "fiber_g": 3.0},
                        "micros": {},
                    },
                    "ranking": {"rank": i + 1, "total_score": 100.0 - i},
                }
                for i in range(n)
            ]
        }

    def test_allocates_one_food_per_exchange_category(self):
        ranked_foods = self._make_ranked_foods("cereal", n=5)
        result = self.allocator.allocate_foods_to_meal(
            meal_name="breakfast",
            exchange_targets={"cereal": 2},
            ranked_foods=ranked_foods,
            day=1,
        )
        assert len(result["allocated_foods"]) == 1
        assert result["allocated_foods"][0]["exchange_category"] == "cereal"

    def test_quantity_equals_exchanges_times_serving_size(self):
        ranked_foods = self._make_ranked_foods("cereal", n=3)
        result = self.allocator.allocate_foods_to_meal(
            meal_name="breakfast",
            exchange_targets={"cereal": 2},
            ranked_foods=ranked_foods,
            day=1,
        )
        food = result["allocated_foods"][0]
        assert food["quantity_g"] == pytest.approx(2 * 30.0)

    def test_nutrition_scaled_to_portion(self):
        ranked_foods = self._make_ranked_foods("cereal", n=3)
        result = self.allocator.allocate_foods_to_meal(
            meal_name="breakfast",
            exchange_targets={"cereal": 1},
            ranked_foods=ranked_foods,
            day=1,
        )
        food = result["allocated_foods"][0]
        # 30g portion of 350kcal/100g food = 105 kcal
        expected_cal = round((350.0 / 100.0) * 30.0, 1)
        assert food["nutrition"]["calories"] == pytest.approx(expected_cal, abs=0.5)

    def test_already_used_food_skipped(self):
        ranked_foods = self._make_ranked_foods("cereal", n=5)
        used_today = {"cereal_0"}
        result = self.allocator.allocate_foods_to_meal(
            meal_name="lunch",
            exchange_targets={"cereal": 1},
            ranked_foods=ranked_foods,
            day=1,
            foods_used_today=used_today,
        )
        allocated_id = result["allocated_foods"][0]["food_id"]
        assert allocated_id != "cereal_0"

    def test_total_nutrition_sums_all_foods(self):
        ranked_foods = {
            **self._make_ranked_foods("cereal", n=5),
            **self._make_ranked_foods("pulse", n=5),
        }
        result = self.allocator.allocate_foods_to_meal(
            meal_name="lunch",
            exchange_targets={"cereal": 1, "pulse": 1},
            ranked_foods=ranked_foods,
            day=1,
        )
        total_cal = result["total_nutrition"]["calories"]
        food_cal_sum = sum(f["nutrition"]["calories"] for f in result["allocated_foods"])
        assert total_cal == pytest.approx(food_cal_sum, abs=0.5)

    def test_missing_category_produces_warning(self):
        result = self.allocator.allocate_foods_to_meal(
            meal_name="dinner",
            exchange_targets={"pulse": 1},
            ranked_foods={},  # No foods at all
            day=1,
        )
        warnings = result["validation"]["warnings"]
        assert any("pulse" in w for w in warnings)

    def test_no_foods_available_returns_empty_allocation(self):
        result = self.allocator.allocate_foods_to_meal(
            meal_name="snack",
            exchange_targets={"cereal": 1},
            ranked_foods={"cereal": []},
            day=1,
        )
        assert result["allocated_foods"] == []
