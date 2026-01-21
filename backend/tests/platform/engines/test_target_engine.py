"""
Tests for Target Engine.

Unit tests for the target engine - testing calorie, macro, and micro calculations.
"""
from uuid import uuid4

import pytest

from app.platform.engines.target_engine.target_engine import TargetEngine
from app.platform.core.context import MNTContext


def make_mnt_context(
    macro_constraints=None,
    micro_constraints=None,
    food_exclusions=None,
    rule_ids=None,
):
    return MNTContext(
        assessment_id=uuid4(),
        macro_constraints=macro_constraints or {},
        micro_constraints=micro_constraints or {},
        food_exclusions=food_exclusions or [],
        rule_ids_used=rule_ids or [],
    )


class TestCalculateCalories:
    """Tests for calorie calculation including BMR/TDEE and MNT constraints."""

    def test_bmr_tdee_defaults(self):
        engine = TargetEngine()
        mnt = make_mnt_context()
        profile = {"weight_kg": 70, "height_cm": 175, "age": 30, "gender": "male"}

        res = engine.calculate_calories(profile, mnt, activity_level="moderately_active")

        assert res["bmr"] is not None
        assert res["tdee"] is not None
        assert res["calories_target"] == pytest.approx(res["tdee"])
        assert res["calculation_source"] == "tdee"

    def test_missing_profile_uses_fallback(self):
        engine = TargetEngine()
        mnt = make_mnt_context()
        profile = {}  # missing fields

        res = engine.calculate_calories(profile, mnt, activity_level=None)

        assert res["calories_target"] == 2000.0
        assert res["calculation_source"] == "custom"

    def test_deficit_percent_applied(self):
        engine = TargetEngine()
        mnt = make_mnt_context(macro_constraints={"calories": {"deficit_percent": 20}})
        profile = {"weight_kg": 70, "height_cm": 175, "age": 30, "gender": "male"}

        res = engine.calculate_calories(profile, mnt, activity_level="sedentary")

        assert res["calculation_source"] == "custom"
        # Ensure deficit applied
        assert res["calories_target"] < res["tdee"]

    def test_min_max_calories_applied(self):
        engine = TargetEngine()
        mnt = make_mnt_context(
            macro_constraints={"calories": {"min": 1800, "max": 1900}}
        )
        profile = {"weight_kg": 70, "height_cm": 175, "age": 30, "gender": "male"}

        res = engine.calculate_calories(profile, mnt, activity_level="lightly_active")

        assert 1800 <= res["calories_target"] <= 1900
        assert res["calculation_source"] == "custom"


class TestCalculateMacros:
    """Tests for macro calculation respecting MNT constraints."""

    def test_default_macros(self):
        engine = TargetEngine()
        mnt = make_mnt_context()
        macros = engine.calculate_macros(2000, {}, mnt)

        assert macros["carbohydrates"]["min_g"] > 0
        assert macros["proteins"]["min_g"] > 0
        assert macros["fats"]["min_g"] > 0

    def test_mnt_restricts_carbs(self):
        engine = TargetEngine()
        mnt = make_mnt_context(
            macro_constraints={"carbohydrates_percent": {"max": 45}}
        )
        macros = engine.calculate_macros(2000, {}, mnt)

        # Max percent should reflect restriction
        assert macros["carbohydrates"]["percent_range"]["max"] == 45
        assert macros["carbohydrates"]["max_g"] == pytest.approx((2000 * 45 / 100) / 4)

    def test_zero_calories_returns_zero_ranges(self):
        engine = TargetEngine()
        mnt = make_mnt_context()
        macros = engine.calculate_macros(0, {}, mnt)

        assert macros["carbohydrates"]["min_g"] == 0
        assert macros["proteins"]["max_g"] == 0
        assert macros["fats"]["max_g"] == 0


class TestCalculateKeyMicros:
    """Tests for micronutrient calculation respecting MNT constraints."""

    def test_default_micros(self):
        engine = TargetEngine()
        mnt = make_mnt_context()
        profile = {"gender": "male", "age": 30}

        micros = engine.calculate_key_micros(profile, mnt)

        assert micros["fiber_g"]["min"] == 25
        assert micros["sodium_mg"]["max"] == 2300
        assert "iron_mg" in micros

    def test_mnt_restricts_sodium(self):
        engine = TargetEngine()
        mnt = make_mnt_context(micro_constraints={"sodium_mg": {"max": 2000}})
        profile = {}

        micros = engine.calculate_key_micros(profile, mnt)

        assert micros["sodium_mg"]["max"] == 2000

    def test_age_adjustments(self):
        engine = TargetEngine()
        mnt = make_mnt_context()
        profile = {"age": 55, "gender": "female"}

        micros = engine.calculate_key_micros(profile, mnt)

        assert micros["calcium_mg"]["min"] == 1200
        assert micros["vitamin_d_iu"]["min"] == 800


class TestCalculateTargets:
    """End-to-end target calculation respecting MNT."""

    def test_full_calculation(self):
        engine = TargetEngine()
        mnt = make_mnt_context(
            macro_constraints={
                "calories": {"deficit_percent": 15},
                "carbohydrates_percent": {"max": 50},
            },
            micro_constraints={"sodium_mg": {"max": 2000}},
        )
        profile = {
            "weight_kg": 70,
            "height_cm": 175,
            "age": 30,
            "gender": "male",
        }

        target_context = engine.calculate_targets(profile, mnt, activity_level="moderately_active")

        assert target_context.calories_target is not None
        assert target_context.macros is not None
        assert target_context.key_micros is not None
        # Ensure constraints respected
        assert target_context.key_micros["sodium_mg"]["max"] == 2000
        assert target_context.macros["carbohydrates"]["percent_range"]["max"] <= 50


