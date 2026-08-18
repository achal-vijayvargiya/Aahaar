"""
Tests for Food Engine, FoodRanker, and FoodDeduplicator.

Structure:
- TestFoodDeduplicator: pure unit tests, no DB required
- TestFoodRanker: pure unit tests, no DB required
- TestFoodEngineIntegration: integration tests against real PostgreSQL (requires KB data)
"""
import pytest
from uuid import uuid4

from app.platform.engines.food_engine.food_engine import FoodEngine
from app.platform.engines.food_engine.food_ranker import FoodRanker, RankingTierConfig
from app.platform.engines.food_engine.food_deduplicator import FoodDeduplicator
from app.platform.core.context import MNTContext, TargetContext, AyurvedaContext


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


def make_target(calories=2000, protein_g=75, carbs_g=250, fat_g=67):
    return TargetContext(
        assessment_id=uuid4(),
        calories_target=calories,
        macros={
            "proteins": {"g": protein_g},
            "carbohydrates": {"g": carbs_g},
            "fats": {"g": fat_g},
        },
    )


def make_food(
    food_id="test_food",
    display_name="Test Food",
    food_type="grain",
    cooking_state="raw",
    serving_size_g=30.0,
    diabetic_safe=False,
    cardiac_safe=False,
    low_carb=False,
    low_sodium=False,
    high_protein=False,
    fiber_g=2.0,
    protein_g=5.0,
    carbs_g=60.0,
    fat_g=2.0,
    calories=300.0,
    exclusion_tags=None,
    inclusion_tags=None,
    compatibility_levels=None,
    preferred_conditions=None,
):
    return {
        "food_id": food_id,
        "display_name": display_name,
        "food_type": food_type,
        "cooking_state": cooking_state,
        "serving_size_per_exchange_g": serving_size_g,
        "mnt_profile": {
            "medical_tags": {
                "diabetic_safe": diabetic_safe,
                "cardiac_safe": cardiac_safe,
            },
            "macro_compliance": {
                "low_carb": low_carb,
                "high_protein": high_protein,
            },
            "micro_compliance": {
                "low_sodium": low_sodium,
            },
            "food_exclusion_tags": exclusion_tags or [],
            "food_inclusion_tags": inclusion_tags or [],
            "contraindications": [],
            "preferred_conditions": preferred_conditions or [],
        },
        "compatibility_levels": compatibility_levels or {},
        "nutrition": {
            "calories": calories,
            "macros": {
                "protein_g": protein_g,
                "carbs_g": carbs_g,
                "fat_g": fat_g,
                "fiber_g": fiber_g,
            },
            "micros": {},
            "calorie_density_kcal_per_g": calories / 100 if calories else None,
            "protein_density_g_per_100kcal": (protein_g / calories * 100) if calories else None,
        },
    }


# ---------------------------------------------------------------------------
# TestFoodDeduplicator
# ---------------------------------------------------------------------------

class TestFoodDeduplicator:

    def setup_method(self):
        self.dedup = FoodDeduplicator(
            enable_scientific_name_matching=True,
            enable_base_name_matching=True,
        )

    def test_extract_scientific_name_present(self):
        name = self.dedup.extract_scientific_name("Wheat (Triticum aestivum)")
        assert name == "triticum aestivum"

    def test_extract_scientific_name_absent(self):
        name = self.dedup.extract_scientific_name("Brown Rice")
        assert name is None

    def test_extract_base_food_name_before_comma(self):
        name = self.dedup.extract_base_food_name("Rice, parboiled")
        assert name == "rice"

    def test_extract_base_food_name_no_comma(self):
        name = self.dedup.extract_base_food_name("Spinach")
        assert name == "spinach"

    def test_extract_base_food_name_strips_scientific(self):
        name = self.dedup.extract_base_food_name("Wheat (Triticum aestivum), whole grain")
        assert name == "wheat"

    def test_get_food_group_key_uses_scientific_first(self):
        food = {"food_id": "wheat_a", "display_name": "Wheat (Triticum aestivum)"}
        key = self.dedup.get_food_group_key(food)
        assert key == "scientific:triticum aestivum"

    def test_get_food_group_key_falls_back_to_base(self):
        food = {"food_id": "rice_a", "display_name": "Rice, white"}
        key = self.dedup.get_food_group_key(food)
        assert key == "base:rice"

    def test_get_food_group_key_none_for_empty_name(self):
        food = {"food_id": "unknown", "display_name": ""}
        key = self.dedup.get_food_group_key(food)
        assert key is None

    def test_deduplicate_collapses_same_group(self):
        foods = [
            {"food_id": "wheat_whole", "display_name": "Wheat (Triticum aestivum), whole"},
            {"food_id": "wheat_refined", "display_name": "Wheat (Triticum aestivum), refined"},
        ]
        result = self.dedup.deduplicate_foods(foods, keep_best_ranked=False)
        assert len(result) == 1
        assert result[0]["food_id"] == "wheat_whole"

    def test_deduplicate_records_variation_metadata(self):
        foods = [
            {"food_id": "wheat_whole", "display_name": "Wheat (Triticum aestivum), whole"},
            {"food_id": "wheat_refined", "display_name": "Wheat (Triticum aestivum), refined"},
        ]
        result = self.dedup.deduplicate_foods(foods, keep_best_ranked=False)
        dedup_meta = result[0]["ranking"]["deduplication"]
        assert dedup_meta["variations_found"] == 2
        assert "wheat_refined" in dedup_meta["variation_food_ids"]

    def test_deduplicate_keep_best_ranked_selects_lower_rank_number(self):
        foods = [
            {"food_id": "wheat_b", "display_name": "Wheat (Triticum aestivum), b", "ranking": {"rank": 5}},
            {"food_id": "wheat_a", "display_name": "Wheat (Triticum aestivum), a", "ranking": {"rank": 2}},
        ]
        result = self.dedup.deduplicate_foods(foods, keep_best_ranked=True)
        assert len(result) == 1
        assert result[0]["food_id"] == "wheat_a"

    def test_deduplicate_different_groups_both_kept(self):
        foods = [
            {"food_id": "rice_1", "display_name": "Rice, white"},
            {"food_id": "lentil_1", "display_name": "Lentil, red"},
        ]
        result = self.dedup.deduplicate_foods(foods, keep_best_ranked=False)
        assert len(result) == 2

    def test_deduplicate_empty_list(self):
        result = self.dedup.deduplicate_foods([])
        assert result == []

    def test_deduplicate_ungrouped_food_passed_through(self):
        foods = [{"food_id": "x", "display_name": ""}]
        result = self.dedup.deduplicate_foods(foods)
        assert len(result) == 1
        assert result[0]["food_id"] == "x"

    def test_scientific_matching_disabled_falls_back_to_base(self):
        dedup_no_sci = FoodDeduplicator(
            enable_scientific_name_matching=False,
            enable_base_name_matching=True,
        )
        key = dedup_no_sci.get_food_group_key(
            {"food_id": "wheat_a", "display_name": "Wheat (Triticum aestivum), whole"}
        )
        assert key == "base:wheat"


# ---------------------------------------------------------------------------
# TestFoodRanker
# ---------------------------------------------------------------------------

class TestFoodRanker:

    def setup_method(self):
        self.ranker = FoodRanker()
        self.mnt = make_mnt()
        self.target = make_target()

    def test_empty_input_returns_empty(self):
        result = self.ranker.rank_foods([], medical_conditions=[], mnt_context=self.mnt, target_context=self.target)
        assert result == []

    def test_output_has_ranking_metadata(self):
        foods = [make_food("f1")]
        result = self.ranker.rank_foods(foods, medical_conditions=[], mnt_context=self.mnt, target_context=self.target)
        assert "ranking" in result[0]
        assert "total_score" in result[0]["ranking"]
        assert "tier_scores" in result[0]["ranking"]
        assert result[0]["ranking"]["rank"] == 1

    def test_rank_positions_are_sequential(self):
        foods = [make_food(f"food_{i}") for i in range(5)]
        result = self.ranker.rank_foods(foods, medical_conditions=[], mnt_context=self.mnt, target_context=self.target)
        ranks = [f["ranking"]["rank"] for f in result]
        assert ranks == list(range(1, 6))

    def test_diabetic_safe_food_ranks_above_neutral(self):
        diabetic_safe = make_food(
            "safe_food",
            diabetic_safe=True,
            compatibility_levels={"diabetes": "safe"},
        )
        neutral = make_food("neutral_food")
        foods = [neutral, diabetic_safe]
        result = self.ranker.rank_foods(
            foods,
            medical_conditions=["diabetes"],
            mnt_context=self.mnt,
            target_context=self.target,
        )
        ranked_ids = [f["food_id"] for f in result]
        assert ranked_ids[0] == "safe_food"

    def test_compatibility_safe_adds_score(self):
        food_compat = make_food("compat_food", compatibility_levels={"hypertension": "safe"})
        food_none = make_food("plain_food")
        result = self.ranker.rank_foods(
            [food_none, food_compat],
            medical_conditions=["hypertension"],
            mnt_context=self.mnt,
            target_context=self.target,
        )
        assert result[0]["food_id"] == "compat_food"

    def test_ayurveda_preferred_food_ranks_higher(self):
        ayu = AyurvedaContext(
            assessment_id=uuid4(),
            dosha_primary="vata",
            vikriti_notes={
                "food_preferences": [
                    {"food_id": "ginger", "preference_type": "prefer"},
                ]
            },
        )
        preferred = make_food("ginger")
        neutral = make_food("spinach")
        result = self.ranker.rank_foods(
            [neutral, preferred],
            medical_conditions=[],
            mnt_context=self.mnt,
            target_context=self.target,
            ayurveda_context=ayu,
        )
        assert result[0]["food_id"] == "ginger"
        assert result[0]["ranking"]["tier_scores"].get("ayurveda_alignment", 0) > 0

    def test_ayurveda_avoided_food_ranks_lower(self):
        ayu = AyurvedaContext(
            assessment_id=uuid4(),
            dosha_primary="pitta",
            vikriti_notes={
                "food_preferences": [
                    {"food_id": "chili", "preference_type": "avoid"},
                ]
            },
        )
        avoided = make_food("chili")
        neutral = make_food("rice")
        result = self.ranker.rank_foods(
            [avoided, neutral],
            medical_conditions=[],
            mnt_context=self.mnt,
            target_context=self.target,
            ayurveda_context=ayu,
        )
        assert result[-1]["food_id"] == "chili"

    def test_recently_used_food_ranks_lower(self):
        recent = make_food("recently_used")
        fresh = make_food("fresh_food")
        result = self.ranker.rank_foods(
            [recent, fresh],
            medical_conditions=[],
            mnt_context=self.mnt,
            target_context=self.target,
            rotation_history=["recently_used", "other1", "other2"],
        )
        assert result[0]["food_id"] == "fresh_food"

    def test_liked_food_ranks_higher(self):
        liked = make_food("liked_food")
        plain = make_food("plain_food")
        result = self.ranker.rank_foods(
            [plain, liked],
            medical_conditions=[],
            mnt_context=self.mnt,
            target_context=self.target,
            client_preferences={"likes": ["liked_food"]},
        )
        assert result[0]["food_id"] == "liked_food"

    def test_high_fiber_food_gets_higher_nutrition_score(self):
        high_fiber = make_food("high_fiber", fiber_g=6.0)
        low_fiber = make_food("low_fiber", fiber_g=0.5)
        result = self.ranker.rank_foods(
            [low_fiber, high_fiber],
            medical_conditions=[],
            mnt_context=self.mnt,
            target_context=self.target,
        )
        assert result[0]["food_id"] == "high_fiber"
        assert result[0]["ranking"]["tier_scores"]["nutrition_alignment"] > result[1]["ranking"]["tier_scores"]["nutrition_alignment"]

    def test_medical_safety_tier_disabled_ignores_conditions(self):
        config = RankingTierConfig(enable_medical_safety=False)
        ranker = FoodRanker(tier_config=config)
        diabetic_safe = make_food("safe", diabetic_safe=True, compatibility_levels={"diabetes": "safe"})
        plain = make_food("plain")
        result = ranker.rank_foods(
            [plain, diabetic_safe],
            medical_conditions=["diabetes"],
            mnt_context=self.mnt,
            target_context=self.target,
        )
        assert "medical_safety" not in result[0]["ranking"]["tier_scores"]

    def test_all_tiers_disabled_still_returns_all_foods(self):
        config = RankingTierConfig(
            enable_medical_safety=False,
            enable_nutrition_alignment=False,
            enable_ayurveda_alignment=False,
            enable_variety=False,
            enable_preferences=False,
            enable_practical=False,
        )
        ranker = FoodRanker(tier_config=config)
        foods = [make_food(f"f{i}") for i in range(3)]
        result = ranker.rank_foods(foods, medical_conditions=[], mnt_context=self.mnt, target_context=self.target)
        assert len(result) == 3

    def test_low_carb_mnt_compliance_scores_high(self):
        # MNT compliance scoring only runs when medical_conditions is non-empty
        # (the medical safety tier returns early if no conditions given).
        low_carb_food = make_food("low_carb", low_carb=True)
        normal_food = make_food("normal")
        mnt_with_carb_max = make_mnt(macro={"carbs_g": {"max": 150}})
        result = self.ranker.rank_foods(
            [normal_food, low_carb_food],
            medical_conditions=["diabetes"],
            mnt_context=mnt_with_carb_max,
            target_context=self.target,
        )
        assert result[0]["food_id"] == "low_carb"

    def test_ranking_tier_config_default_weights_sum_to_one(self):
        config = RankingTierConfig()
        config.normalize_weights()
        total = (
            config.medical_safety_weight
            + config.nutrition_alignment_weight
            + config.ayurveda_alignment_weight
            + config.variety_weight
            + config.preferences_weight
            + config.practical_weight
        )
        assert abs(total - 1.0) < 1e-9

    def test_original_food_dict_not_mutated(self):
        food = make_food("f1")
        original_keys = set(food.keys())
        foods_copy = [food.copy()]
        self.ranker.rank_foods(foods_copy, medical_conditions=[], mnt_context=self.mnt, target_context=self.target)
        assert set(food.keys()) == original_keys


# ---------------------------------------------------------------------------
# TestFoodEngineIntegration  (requires PostgreSQL with KB food data)
# ---------------------------------------------------------------------------

class TestFoodEngineIntegration:
    """
    Integration tests for FoodEngine against real PostgreSQL + KB food data.
    These tests will return empty results (but not crash) if the DB has no KB data.
    Mark individual tests xfail if KB data is not guaranteed in CI.
    """

    def test_get_foods_by_category_simple_returns_list(self, platform_db):
        engine = FoodEngine()
        result = engine.get_foods_by_category_simple(
            db=platform_db,
            exchange_category="cereal",
            food_exclusions=[],
            medical_conditions=None,
        )
        assert isinstance(result, list)

    def test_get_foods_by_category_simple_food_structure(self, platform_db):
        engine = FoodEngine()
        result = engine.get_foods_by_category_simple(
            db=platform_db,
            exchange_category="cereal",
            food_exclusions=[],
            medical_conditions=None,
        )
        for food in result:
            assert "food_id" in food
            assert "display_name" in food
            assert "exchange_category" in food
            assert food["exchange_category"] == "cereal"

    def test_get_foods_by_category_excludes_fried_foods(self, platform_db):
        engine = FoodEngine()
        result = engine.get_foods_by_category_simple(
            db=platform_db,
            exchange_category="cereal",
            food_exclusions=["fried_foods"],
            medical_conditions=None,
        )
        for food in result:
            tags = food.get("food_exclusion_tags", [])
            assert "fried_foods" not in tags, (
                f"Food {food['food_id']} has fried_foods tag but was not excluded"
            )

    def test_get_foods_by_category_with_diabetes_excludes_contraindicated(self, platform_db):
        engine = FoodEngine()
        result = engine.get_foods_by_category_simple(
            db=platform_db,
            exchange_category="cereal",
            food_exclusions=[],
            medical_conditions=["diabetes"],
        )
        for food in result:
            compat_levels = food.get("compatibility_levels", {})
            for condition, level in compat_levels.items():
                assert level != "contraindicated", (
                    f"Food {food['food_id']} is contraindicated for {condition} but was included"
                )

    def test_get_foods_by_category_simple_dict_returns_all_categories(self, platform_db):
        engine = FoodEngine()
        categories = ["cereal", "pulse"]
        result = engine.get_foods_by_category_simple_dict(
            db=platform_db,
            exchange_categories=categories,
            food_exclusions=[],
        )
        assert isinstance(result, dict)
        assert "cereal" in result
        assert "pulse" in result

    def test_get_foods_by_category_no_db_raises(self):
        engine = FoodEngine()
        with pytest.raises(ValueError, match="Database session is required"):
            engine.get_foods_by_category_simple(
                db=None,
                exchange_category="cereal",
                food_exclusions=[],
            )

    def test_get_foods_by_category_no_category_raises(self, platform_db):
        engine = FoodEngine()
        with pytest.raises(ValueError, match="Exchange category is required"):
            engine.get_foods_by_category_simple(
                db=platform_db,
                exchange_category="",
                food_exclusions=[],
            )
