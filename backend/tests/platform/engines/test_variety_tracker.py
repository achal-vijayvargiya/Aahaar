"""
Unit tests for VarietyTracker.

Tests both variety rules:
- Rule A: Same-Day Variety (no food repeats within the same day)
- Rule B: Cross-Day Combination Variety (same meal combination not repeated on consecutive days)

Pure unit tests — no DB required.
"""
import pytest
from app.platform.engines.recipe_engine.variety_tracker import VarietyTracker


class TestVarietyTrackerRuleA:
    """Rule A: Same-Day Variety — no food repeats across meals on the same day."""

    def setup_method(self):
        self.tracker = VarietyTracker()

    def test_unused_food_is_allowed(self):
        can_use, reason = self.tracker.can_use_food("rice", "breakfast", day=1)
        assert can_use is True
        assert reason == ""

    def test_food_allowed_before_recording(self):
        can_use, _ = self.tracker.can_use_food("rice", "lunch", day=1)
        assert can_use is True

    def test_food_blocked_after_recording_same_day(self):
        self.tracker.record_food_usage("rice", "breakfast", day=1)
        can_use, reason = self.tracker.can_use_food("rice", "lunch", day=1)
        assert can_use is False
        assert "Rule A" in reason

    def test_food_blocked_across_all_meals_same_day(self):
        self.tracker.record_food_usage("wheat", "breakfast", day=2)
        for meal in ("lunch", "dinner", "snack"):
            can_use, _ = self.tracker.can_use_food("wheat", meal, day=2)
            assert can_use is False, f"wheat should be blocked at {meal} on day 2"

    def test_different_food_not_affected(self):
        self.tracker.record_food_usage("rice", "breakfast", day=1)
        can_use, _ = self.tracker.can_use_food("lentil", "lunch", day=1)
        assert can_use is True

    def test_food_allowed_on_different_day(self):
        self.tracker.record_food_usage("rice", "breakfast", day=1)
        can_use, _ = self.tracker.can_use_food("rice", "breakfast", day=2)
        assert can_use is True

    def test_multiple_foods_tracked_independently(self):
        self.tracker.record_food_usage("rice", "breakfast", day=3)
        self.tracker.record_food_usage("dal", "breakfast", day=3)
        assert self.tracker.can_use_food("rice", "dinner", day=3)[0] is False
        assert self.tracker.can_use_food("dal", "dinner", day=3)[0] is False
        assert self.tracker.can_use_food("spinach", "dinner", day=3)[0] is True

    def test_get_foods_used_today_returns_correct_set(self):
        self.tracker.record_food_usage("rice", "breakfast", day=1)
        self.tracker.record_food_usage("dal", "lunch", day=1)
        used = self.tracker.get_foods_used_today(day=1)
        assert "rice" in used
        assert "dal" in used
        assert "spinach" not in used

    def test_get_foods_used_today_empty_for_new_day(self):
        used = self.tracker.get_foods_used_today(day=5)
        assert used == set()


class TestVarietyTrackerRuleB:
    """Rule B: Cross-Day Combination Variety — same combo cannot repeat on consecutive days."""

    def setup_method(self):
        self.tracker = VarietyTracker()

    def test_new_combination_allowed(self):
        can_use, reason = self.tracker.can_use_meal_combination(
            "lunch", day=1, food_ids={"rice", "dal"}
        )
        assert can_use is True
        assert reason == ""

    def test_empty_combination_always_allowed(self):
        can_use, _ = self.tracker.can_use_meal_combination("lunch", day=2, food_ids=set())
        assert can_use is True

    def test_same_combo_consecutive_days_blocked(self):
        self.tracker.record_meal_combination("lunch", day=1, food_ids={"rice", "dal", "spinach"})
        can_use, reason = self.tracker.can_use_meal_combination(
            "lunch", day=2, food_ids={"rice", "dal", "spinach"}
        )
        assert can_use is False
        assert "Rule B" in reason

    def test_different_combo_consecutive_days_allowed(self):
        self.tracker.record_meal_combination("lunch", day=1, food_ids={"rice", "dal"})
        can_use, _ = self.tracker.can_use_meal_combination(
            "lunch", day=2, food_ids={"wheat", "chana"}
        )
        assert can_use is True

    def test_partially_different_combo_allowed(self):
        self.tracker.record_meal_combination("lunch", day=1, food_ids={"rice", "dal"})
        can_use, _ = self.tracker.can_use_meal_combination(
            "lunch", day=2, food_ids={"rice", "chana"}
        )
        assert can_use is True

    def test_same_combo_non_consecutive_days_allowed(self):
        self.tracker.record_meal_combination("lunch", day=1, food_ids={"rice", "dal"})
        can_use, _ = self.tracker.can_use_meal_combination(
            "lunch", day=3, food_ids={"rice", "dal"}
        )
        assert can_use is True

    def test_different_meal_same_combo_allowed(self):
        self.tracker.record_meal_combination("lunch", day=1, food_ids={"rice", "dal"})
        can_use, _ = self.tracker.can_use_meal_combination(
            "dinner", day=2, food_ids={"rice", "dal"}
        )
        assert can_use is True

    def test_get_previous_day_combination_returns_correct_set(self):
        self.tracker.record_meal_combination("breakfast", day=2, food_ids={"oats", "milk"})
        prev = self.tracker.get_previous_day_combination("breakfast", day=3)
        assert prev == {"oats", "milk"}

    def test_get_previous_day_combination_empty_when_no_history(self):
        prev = self.tracker.get_previous_day_combination("breakfast", day=1)
        assert prev == set()

    def test_combination_order_does_not_matter(self):
        self.tracker.record_meal_combination("dinner", day=4, food_ids={"a", "b", "c"})
        can_use, _ = self.tracker.can_use_meal_combination(
            "dinner", day=5, food_ids={"c", "a", "b"}
        )
        assert can_use is False


class TestVarietyTrackerReset:

    def test_reset_clears_daily_foods(self):
        tracker = VarietyTracker()
        tracker.record_food_usage("rice", "breakfast", day=1)
        tracker.reset()
        assert tracker.daily_foods == {}
        can_use, _ = tracker.can_use_food("rice", "breakfast", day=1)
        assert can_use is True

    def test_reset_clears_meal_combinations(self):
        tracker = VarietyTracker()
        tracker.record_meal_combination("lunch", day=1, food_ids={"rice", "dal"})
        tracker.reset()
        assert tracker.meal_combinations == {}
        can_use, _ = tracker.can_use_meal_combination("lunch", day=2, food_ids={"rice", "dal"})
        assert can_use is True

    def test_fresh_tracker_has_empty_state(self):
        tracker = VarietyTracker()
        assert tracker.daily_foods == {}
        assert tracker.meal_combinations == {}


class TestVarietyTrackerSevenDayScenario:
    """Simulate a realistic 7-day scenario to validate variety across the full week."""

    def test_rule_a_across_seven_days(self):
        tracker = VarietyTracker()
        # Record different breakfast foods each day
        breakfast_foods = ["oats", "upma", "idli", "poha", "dosa", "paratha", "roti"]
        for day, food in enumerate(breakfast_foods, start=1):
            can_use, _ = tracker.can_use_food(food, "breakfast", day=day)
            assert can_use is True
            tracker.record_food_usage(food, "breakfast", day=day)
            # Verify same food blocked at lunch on the same day
            blocked, _ = tracker.can_use_food(food, "lunch", day=day)
            assert blocked is False

    def test_rule_b_across_seven_days(self):
        tracker = VarietyTracker()
        combos = [
            {"rice", "sambar"},
            {"wheat", "dal"},
            {"rice", "rajma"},
            {"millet", "dal"},
            {"rice", "chole"},
            {"wheat", "sambar"},
            {"rice", "lentil"},
        ]
        for day, combo in enumerate(combos, start=1):
            can_use, _ = tracker.can_use_meal_combination("lunch", day=day, food_ids=combo)
            assert can_use is True, f"Day {day} combo should be allowed"
            tracker.record_meal_combination("lunch", day=day, food_ids=combo)

    def test_rule_b_blocked_when_consecutive_days_repeat(self):
        tracker = VarietyTracker()
        combo = {"rice", "dal", "sabzi"}
        tracker.record_meal_combination("dinner", day=1, food_ids=combo)
        can_use, _ = tracker.can_use_meal_combination("dinner", day=2, food_ids=combo)
        assert can_use is False
