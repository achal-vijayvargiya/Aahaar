"""
Tests for Ayurveda Engine.

Unit tests for dosha assessment and guidelines/preferences respecting MNT constraints.
"""
from uuid import uuid4

from app.platform.engines.ayurveda_engine.ayurveda_engine import AyurvedaEngine
from app.platform.core.context import MNTContext, TargetContext


def make_mnt_context(food_exclusions=None, macro=None, micro=None):
    return MNTContext(
        assessment_id=uuid4(),
        macro_constraints=macro or {},
        micro_constraints=micro or {},
        food_exclusions=food_exclusions or [],
        rule_ids_used=[],
    )


class TestAssessDosha:
    def test_quiz_scores_used(self):
        engine = AyurvedaEngine()
        client_profile = {"age": 30}
        intake_data = {"ayurveda_quiz": {"dosha_scores": {"pitta": 8, "vata": 2, "kapha": 1}}}

        res = engine.assess_dosha(client_profile, intake_data=intake_data)

        assert res["dosha_primary"] == "pitta"
        assert res["dosha_scores"]["pitta"] == 8

    def test_bmi_high_prefers_kapha(self):
        engine = AyurvedaEngine()
        client_profile = {"weight_kg": 90, "height_cm": 170}

        res = engine.assess_dosha(client_profile)

        assert res["dosha_primary"] == "kapha"

    def test_bloating_prefers_vata(self):
        engine = AyurvedaEngine()
        client_profile = {}
        intake_data = {"symptoms": ["bloating"]}

        res = engine.assess_dosha(client_profile, intake_data=intake_data)

        assert res["dosha_primary"] == "vata"

    def test_acidity_prefers_pitta(self):
        engine = AyurvedaEngine()
        client_profile = {}
        intake_data = {"symptoms": ["acidity"]}

        res = engine.assess_dosha(client_profile, intake_data=intake_data)

        assert res["dosha_primary"] == "pitta"


class TestGuidelinesAndPreferences:
    def test_guidelines_respect_exclusions(self):
        engine = AyurvedaEngine()
        mnt = make_mnt_context(food_exclusions=["ginger"])
        dosha = {"dosha_primary": "vata"}

        guidelines = engine.generate_lifestyle_guidelines(dosha, mnt)
        spices = guidelines["spices"]["recommendation"]

        assert "ginger" not in spices

    def test_preferences_respect_exclusions(self):
        engine = AyurvedaEngine()
        mnt = make_mnt_context(food_exclusions=["ginger", "fried"])
        dosha = {"dosha_primary": "kapha"}

        prefs = engine.generate_food_preferences(dosha, mnt)
        food_ids = [p["food_id"] for p in prefs]

        assert "ginger" not in food_ids
        assert "fried" not in food_ids

    def test_process_returns_context(self):
        engine = AyurvedaEngine()
        mnt = make_mnt_context()
        target = TargetContext(assessment_id=mnt.assessment_id)
        client_profile = {"age": 30, "gender": "male", "height_cm": 175, "weight_kg": 70}

        ctx = engine.process_ayurveda_assessment(client_profile, mnt, target)

        assert ctx.assessment_id == mnt.assessment_id
        # Dosha may be None if no signals; ensure context returned
        assert ctx.vikriti_notes is not None
        assert ctx.lifestyle_guidelines is not None

