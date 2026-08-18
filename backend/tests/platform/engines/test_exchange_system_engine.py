"""Unit tests for ExchangeSystemEngine (no database)."""
from uuid import uuid4

import pytest

from app.platform.core.context import MealStructureContext, TargetContext, MNTContext
from app.platform.engines.exchange_system_engine.exchange_system_engine import (
    ExchangeSystemEngine,
)


@pytest.fixture
def sample_meal_structure():
    aid = uuid4()
    return MealStructureContext(
        assessment_id=aid,
        meal_count=4,
        meals=["breakfast", "lunch", "snack", "dinner"],
        timing_windows={
            "breakfast": ["07:30", "09:00"],
            "lunch": ["12:30", "14:00"],
            "snack": ["16:00", "17:00"],
            "dinner": ["19:30", "21:00"],
        },
        energy_weight={
            "breakfast": 0.225,
            "lunch": 0.325,
            "snack": 0.15,
            "dinner": 0.30,
        },
    )


@pytest.fixture
def sample_target():
    return TargetContext(
        assessment_id=uuid4(),
        calories_target=1800.0,
        macros={
            "proteins": {"g": 70.0},
            "carbohydrates": {"g": 200.0},
            "fats": {"g": 60.0},
        },
    )


@pytest.fixture
def sample_mnt():
    return MNTContext(assessment_id=uuid4())


class TestGenerateExchanges:
    def test_without_user_mandatory_produces_non_empty_allocations(
        self, sample_meal_structure, sample_target, sample_mnt
    ):
        """Full NCP path does not pass user_mandatory_exchanges_per_meal; engine must still allocate."""
        engine = ExchangeSystemEngine()
        result = engine.generate_exchanges(
            meal_structure=sample_meal_structure,
            target_context=sample_target,
            mnt_context=sample_mnt,
            ayurveda_context=None,
            user_mandatory_exchanges=None,
            user_mandatory_exchanges_per_meal=None,
        )
        daily = result.get("daily_exchange_allocation") or {}
        per_meal = result.get("per_meal_allocation") or {}
        assert len(daily) > 0, "daily_exchange_allocation should not be empty without UI mandatories"
        for meal in sample_meal_structure.meals:
            assert meal in per_meal, f"missing meal {meal} in per_meal_allocation"
            assert len(per_meal[meal]) > 0, f"meal {meal} should have exchange categories"

    def test_with_user_mandatory_still_works(
        self, sample_meal_structure, sample_target, sample_mnt
    ):
        engine = ExchangeSystemEngine()
        result = engine.generate_exchanges(
            meal_structure=sample_meal_structure,
            target_context=sample_target,
            mnt_context=sample_mnt,
            user_mandatory_exchanges_per_meal={
                "breakfast": ["pulse", "milk"],
                "lunch": ["pulse", "cereal"],
                "snack": ["fruit"],
                "dinner": ["pulse", "vegetable_non_starchy"],
            },
        )
        per_meal = result["per_meal_allocation"]
        assert "pulse" in per_meal["breakfast"] or any(
            v > 0 for v in per_meal["breakfast"].values()
        )
