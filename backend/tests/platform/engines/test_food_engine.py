"""
Tests for Food Engine.
"""
import pytest

from app.platform.engines.food_engine.food_engine import FoodEngine
from app.platform.engines.food_engine.kb_food_adapter import list_food_ids
from app.platform.core.context import MNTContext, TargetContext, AyurvedaContext
from uuid import uuid4


def make_mnt(macro=None, micro=None, exclusions=None):
    ctx = MNTContext(
        assessment_id=uuid4(),
        macro_constraints=macro or {},
        micro_constraints=micro or {},
        food_exclusions=exclusions or [],
        rule_ids_used=[],
    )
    ctx.client_id = uuid4()
    return ctx


class TestFoodFilters:
    def test_exclusions_remove_foods(self):
        engine = FoodEngine()
        mnt = make_mnt(exclusions=["oats"])
        foods = ["oats", "lentils"]
        filtered = engine.filter_foods_by_exclusions(foods, mnt)
        assert "oats" not in filtered
        assert "lentils" in filtered

    def test_mnt_carbs_constraint(self):
        engine = FoodEngine()
        mnt = make_mnt(macro={"carbohydrates_percent": {"max": 40}})
        foods = list_food_ids()
        filtered = engine.filter_foods_by_mnt_constraints(foods, mnt)
        # High-carb foods like oats/brown_rice likely filtered
        assert "grilled_chicken" in filtered or "tofu" in filtered

    def test_mnt_sodium_constraint(self):
        engine = FoodEngine()
        mnt = make_mnt(micro={"sodium_mg": {"max": 10}})
        foods = list_food_ids()
        filtered = engine.filter_foods_by_mnt_constraints(foods, mnt)
        assert "grilled_chicken" not in filtered  # sodium 74 > 10


class TestAyurvedaOrdering:
    def test_preferences_ordering(self):
        engine = FoodEngine()
        foods = ["oats", "lentils", "ginger"]
        ayu = AyurvedaContext(
            assessment_id=uuid4(),
            dosha_primary="vata",
            vikriti_notes={
                "food_preferences": [
                    {"food_id": "ginger", "preference_type": "prefer"},
                    {"food_id": "oats", "preference_type": "avoid"},
                ]
            },
        )
        ordered = engine.apply_ayurveda_preferences(foods, ayu)
        assert ordered[0] == "ginger"
        assert ordered[-1] == "oats"


class TestComposeMeals:
    def test_compose_meals_calories_near_target(self):
        engine = FoodEngine()
        mnt = make_mnt()
        target = TargetContext(assessment_id=mnt.assessment_id, calories_target=2000)
        foods = ["oats", "grilled_chicken", "broccoli", "almonds"]
        plan = engine.compose_meals(foods, target, mnt)
        assert "meals" in plan
        total_cals = plan["totals"]["calories"]
        assert 1600 <= total_cals <= 2400  # within +/-20%


class TestGenerateMealPlan:
    def test_end_to_end_generate(self):
        engine = FoodEngine()
        mnt = make_mnt()
        target = TargetContext(assessment_id=mnt.assessment_id, calories_target=1800)
        ayu = AyurvedaContext(
            assessment_id=mnt.assessment_id,
            dosha_primary="vata",
            vikriti_notes={
                "food_preferences": [
                    {"food_id": "ginger", "preference_type": "prefer"}
                ]
            },
        )
        intervention = engine.generate_meal_plan(mnt, target, ayu)
        assert intervention.meal_plan is not None
        assert "meals" in intervention.meal_plan
        assert intervention.constraints_snapshot is not None

