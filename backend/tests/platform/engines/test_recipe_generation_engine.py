"""
Unit tests for RecipeGenerationEngine using mocked LLM calls.

No OpenRouter API key required — all LLM calls are intercepted via unittest.mock.

Tests cover:
- Init guard (raises on empty/placeholder API key)
- Valid LLM response: correct output structure
- LLM failure: graceful degradation (no crash, warning in output)
- Validation: recipe with no ingredients flagged invalid
- Multi-day generate_recipes_for_meal_plan: summary counts are correct
"""
import json
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from uuid import uuid4

from app.platform.engines.recipe_engine.recipe_generation_engine import RecipeGenerationEngine
from app.platform.core.context import MNTContext, AyurvedaContext


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FAKE_API_KEY = "sk-or-v1-fake-test-key-for-unit-tests-only"
SIMPLE_TEMPLATE = (
    "Generate a recipe for {{MEAL_NAME}} on {{DAY}}.\n"
    "Foods: {{FOOD_LIST_WITH_GRAMS}}\n"
    "Constraints: {{MEDICAL_CONSTRAINTS_SUMMARY}} {{AYURVEDA_CONSTRAINTS_SUMMARY}}\n"
    "Oil: {{OIL_LIMIT_ML}}ml\n"
    "GENERATE THE FINAL RECIPE NOW"
)


def _make_engine_patched():
    """
    Build a RecipeGenerationEngine with a real API key string but a mocked OpenAI
    client and mocked prompt template, so no file I/O or network calls occur.
    """
    with patch(
        "app.platform.engines.recipe_engine.recipe_generation_engine.OpenAI"
    ) as mock_openai_cls, patch.object(
        RecipeGenerationEngine, "_load_prompt_template", return_value=SIMPLE_TEMPLATE
    ):
        engine = RecipeGenerationEngine(api_key=FAKE_API_KEY)
        engine.client = mock_openai_cls.return_value  # keep the mock client
    return engine


def _make_valid_llm_response(allocated_foods):
    """Build a valid recipe dict that the engine's validator should accept."""
    ingredients = [
        f"{food.get('display_name', food['food_id'])} – {food.get('quantity_g', 30)}g"
        for food in allocated_foods
    ]
    return {
        "dish_name": "Test Dish",
        "ingredients": ingredients,
        "cooking_steps": ["Step 1: Mix ingredients", "Step 2: Cook for 10 minutes"],
        "approx_cooking_time_minutes": 15,
        "serving_instructions": "Serve hot with chutney.",
    }


def _make_meal_data(food_ids=None):
    """Minimal meal_data matching what MealAllocationEngine produces."""
    food_ids = food_ids or ["wheat_flour", "milk"]
    foods = [
        {
            "food_id": fid,
            "display_name": fid.replace("_", " ").title(),
            "exchange_category": "cereal",
            "exchanges": 2,
            "quantity_g": 60.0,
            "nutrition": {"calories": 200.0, "protein_g": 6.0, "carbs_g": 40.0, "fat_g": 2.0},
        }
        for fid in food_ids
    ]
    return {
        "allocated_foods": foods,
        "total_nutrition": {"calories": 200.0},
        "exchanges_used": {"cereal": 2},
        "validation": {"is_valid": True, "warnings": []},
    }


def _make_meal_plan(days=1):
    """Build a minimal meal_plan matching MealAllocationEngine output."""
    days_dict = {}
    for d in range(1, days + 1):
        days_dict[f"day_{d}"] = {
            "day_number": d,
            "date": f"2025-01-{d:02d}",
            "day_name": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][d - 1],
            "meals": {
                "breakfast": _make_meal_data(["oats", "milk"]),
                "lunch": _make_meal_data(["rice", "dal"]),
            },
        }
    return {"days": days_dict}


# ---------------------------------------------------------------------------
# TestRecipeGenerationEngineInit
# ---------------------------------------------------------------------------

class TestRecipeGenerationEngineInit:

    def test_raises_on_empty_api_key(self):
        # api_key="" falls through to settings.OPENROUTER_API_KEY, so mock that too
        with patch(
            "app.platform.engines.recipe_engine.recipe_generation_engine.settings"
        ) as mock_settings:
            mock_settings.OPENROUTER_API_KEY = None
            mock_settings.DIET_PLAN_MODEL = "test-model"
            with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
                RecipeGenerationEngine(api_key="")

    def test_raises_on_placeholder_api_key(self):
        with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
            RecipeGenerationEngine(api_key="sk-or-v1-placeholder-get-from-openrouter-ai")

    def test_raises_on_none_api_key(self):
        with patch("app.platform.engines.recipe_engine.recipe_generation_engine.settings") as mock_settings:
            mock_settings.OPENROUTER_API_KEY = None
            mock_settings.DIET_PLAN_MODEL = "test-model"
            with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
                RecipeGenerationEngine(api_key=None)

    def test_valid_api_key_creates_engine(self):
        with patch(
            "app.platform.engines.recipe_engine.recipe_generation_engine.OpenAI"
        ), patch.object(RecipeGenerationEngine, "_load_prompt_template", return_value=SIMPLE_TEMPLATE):
            engine = RecipeGenerationEngine(api_key=FAKE_API_KEY)
        assert engine is not None
        assert engine.api_key == FAKE_API_KEY


# ---------------------------------------------------------------------------
# TestGenerateRecipeForMeal
# ---------------------------------------------------------------------------

class TestGenerateRecipeForMeal:

    def setup_method(self):
        self.engine = _make_engine_patched()

    def _mock_llm_response(self, recipe_dict):
        """Set up the mock LLM to return the given recipe dict as JSON."""
        mock_choice = MagicMock()
        mock_choice.message.content = json.dumps(recipe_dict)
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        self.engine.client.chat.completions.create.return_value = mock_response

    def test_valid_response_produces_recipe(self):
        meal_data = _make_meal_data(["wheat_flour", "milk"])
        recipe = _make_valid_llm_response(meal_data["allocated_foods"])
        self._mock_llm_response(recipe)

        result = self.engine.generate_recipe_for_meal(
            meal_name="breakfast",
            meal_data=meal_data,
            day_name="Monday",
            mnt_summary="",
            ayurveda_summary="",
            oil_limit=5.0,
        )
        assert result["recipe"] is not None
        assert result["recipe"]["dish_name"] == "Test Dish"
        assert len(result["recipe"]["cooking_steps"]) == 2

    def test_valid_response_preserves_allocated_foods(self):
        meal_data = _make_meal_data(["wheat_flour", "milk"])
        recipe = _make_valid_llm_response(meal_data["allocated_foods"])
        self._mock_llm_response(recipe)

        result = self.engine.generate_recipe_for_meal(
            meal_name="breakfast",
            meal_data=meal_data,
            day_name="Tuesday",
            mnt_summary="",
            ayurveda_summary="",
            oil_limit=5.0,
        )
        assert result["allocated_foods"] == meal_data["allocated_foods"]
        assert result["meal_name"] == "breakfast"

    def test_llm_exception_returns_none_recipe_with_warning(self):
        self.engine.client.chat.completions.create.side_effect = RuntimeError("connection timeout")

        meal_data = _make_meal_data(["wheat_flour"])
        result = self.engine.generate_recipe_for_meal(
            meal_name="lunch",
            meal_data=meal_data,
            day_name="Wednesday",
            mnt_summary="",
            ayurveda_summary="",
            oil_limit=5.0,
        )
        assert result["recipe"] is None
        assert result["validation"]["is_valid"] is False
        assert any("LLM call failed" in w or "failed" in w.lower() for w in result["validation"]["warnings"])

    def test_empty_allocated_foods_returns_invalid_immediately(self):
        meal_data = {"allocated_foods": [], "total_nutrition": {}, "exchanges_used": {}, "validation": {}}
        result = self.engine.generate_recipe_for_meal(
            meal_name="snack",
            meal_data=meal_data,
            day_name="Thursday",
            mnt_summary="",
            ayurveda_summary="",
            oil_limit=5.0,
        )
        assert result["recipe"] is None
        assert result["validation"]["is_valid"] is False
        assert "No foods" in result["validation"]["warnings"][0]
        # LLM should not be called at all for empty meals
        self.engine.client.chat.completions.create.assert_not_called()

    def test_llm_empty_response_raises_and_is_caught(self):
        mock_choice = MagicMock()
        mock_choice.message.content = ""
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        self.engine.client.chat.completions.create.return_value = mock_response

        meal_data = _make_meal_data(["rice"])
        result = self.engine.generate_recipe_for_meal(
            meal_name="dinner",
            meal_data=meal_data,
            day_name="Friday",
            mnt_summary="",
            ayurveda_summary="",
            oil_limit=5.0,
        )
        assert result["recipe"] is None
        assert result["validation"]["is_valid"] is False

    def test_llm_invalid_json_is_caught(self):
        mock_choice = MagicMock()
        mock_choice.message.content = "This is not JSON at all {{broken}"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        self.engine.client.chat.completions.create.return_value = mock_response

        meal_data = _make_meal_data(["oats"])
        result = self.engine.generate_recipe_for_meal(
            meal_name="breakfast",
            meal_data=meal_data,
            day_name="Saturday",
            mnt_summary="",
            ayurveda_summary="",
            oil_limit=5.0,
        )
        assert result["recipe"] is None
        assert result["validation"]["is_valid"] is False


# ---------------------------------------------------------------------------
# TestValidateRecipe
# ---------------------------------------------------------------------------

class TestValidateRecipe:
    """Unit tests for the internal _validate_recipe method."""

    def setup_method(self):
        self.engine = _make_engine_patched()
        self.allocated_foods = _make_meal_data(["oats", "milk"])["allocated_foods"]

    def test_valid_recipe_passes_validation(self):
        recipe = _make_valid_llm_response(self.allocated_foods)
        result = self.engine._validate_recipe(recipe, self.allocated_foods)
        assert result["is_valid"] is True
        assert result["warnings"] == []

    def test_none_recipe_fails_validation(self):
        result = self.engine._validate_recipe(None, self.allocated_foods)
        assert result["is_valid"] is False

    def test_recipe_with_no_ingredients_fails(self):
        recipe = {
            "dish_name": "Empty Dish",
            "ingredients": [],
            "cooking_steps": ["Cook"],
            "approx_cooking_time_minutes": 5,
            "serving_instructions": "Serve",
        }
        result = self.engine._validate_recipe(recipe, self.allocated_foods)
        assert result["is_valid"] is False

    def test_recipe_missing_ingredients_key_fails(self):
        recipe = {
            "dish_name": "No Ingredients Key",
            "cooking_steps": ["Cook"],
            "approx_cooking_time_minutes": 5,
            "serving_instructions": "Serve",
        }
        result = self.engine._validate_recipe(recipe, self.allocated_foods)
        assert result["is_valid"] is False


# ---------------------------------------------------------------------------
# TestGenerateRecipesForMealPlan
# ---------------------------------------------------------------------------

class TestGenerateRecipesForMealPlan:
    """Tests for the top-level multi-day generate_recipes_for_meal_plan method."""

    def setup_method(self):
        self.engine = _make_engine_patched()

    def _always_succeed(self, foods):
        """Configure mock LLM to always return a valid recipe."""
        def _side_effect(*args, **kwargs):
            mock_choice = MagicMock()
            # Build a generic valid response referencing the first food's name
            mock_choice.message.content = json.dumps({
                "dish_name": "Mock Dish",
                "ingredients": [f"{f.get('display_name', f['food_id'])} – {f['quantity_g']}g" for f in foods],
                "cooking_steps": ["Mock step 1", "Mock step 2"],
                "approx_cooking_time_minutes": 10,
                "serving_instructions": "Mock serving instructions.",
            })
            mock_response = MagicMock()
            mock_response.choices = [mock_choice]
            return mock_response
        self.engine.client.chat.completions.create.side_effect = _side_effect

    def test_output_has_days_and_summary_keys(self):
        meal_plan = _make_meal_plan(days=1)
        all_foods = [f for d in meal_plan["days"].values() for m in d["meals"].values() for f in m["allocated_foods"]]
        self._always_succeed(all_foods)

        result = self.engine.generate_recipes_for_meal_plan(meal_plan)
        assert "days" in result
        assert "summary" in result

    def test_summary_counts_match_meals(self):
        meal_plan = _make_meal_plan(days=2)  # 2 days × 2 meals = 4 meals total
        all_foods = [f for d in meal_plan["days"].values() for m in d["meals"].values() for f in m["allocated_foods"]]
        self._always_succeed(all_foods)

        result = self.engine.generate_recipes_for_meal_plan(meal_plan)
        summary = result["summary"]
        assert summary["total_meals"] == 4

    def test_successful_recipes_count_correct(self):
        meal_plan = _make_meal_plan(days=1)  # 1 day × 2 meals = 2
        all_foods = [f for d in meal_plan["days"].values() for m in d["meals"].values() for f in m["allocated_foods"]]
        self._always_succeed(all_foods)

        result = self.engine.generate_recipes_for_meal_plan(meal_plan)
        assert result["summary"]["successful_recipes"] == 2
        assert result["summary"]["failed_recipes"] == 0

    def test_llm_failure_counted_as_failed_recipe(self):
        meal_plan = _make_meal_plan(days=1)
        self.engine.client.chat.completions.create.side_effect = RuntimeError("LLM is down")

        result = self.engine.generate_recipes_for_meal_plan(meal_plan)
        summary = result["summary"]
        assert summary["failed_recipes"] == 2  # all 2 meals failed
        assert summary["successful_recipes"] == 0

    def test_phase1_metrics_preserved(self):
        meal_plan = _make_meal_plan(days=1)
        meal_plan["variety_metrics"] = {"total_unique_foods": 4}
        meal_plan["nutrition_summary"] = {"average_daily": {"calories": 1800}}
        meal_plan["start_date"] = "2025-01-01"

        all_foods = [f for d in meal_plan["days"].values() for m in d["meals"].values() for f in m["allocated_foods"]]
        self._always_succeed(all_foods)

        result = self.engine.generate_recipes_for_meal_plan(meal_plan)
        assert result["variety_metrics"]["total_unique_foods"] == 4
        assert result["nutrition_summary"]["average_daily"]["calories"] == 1800
        assert result["start_date"] == "2025-01-01"

    def test_empty_days_returns_zero_counts(self):
        meal_plan = {"days": {}}
        result = self.engine.generate_recipes_for_meal_plan(meal_plan)
        assert result["summary"]["total_meals"] == 0
        assert result["summary"]["successful_recipes"] == 0
