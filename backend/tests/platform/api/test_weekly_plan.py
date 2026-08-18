"""
Tests for weekly plan generation (LangGraph supervisor): policy rules and API pipeline modes.
"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.platform.data.repositories.platform_assessment_repository import (
    PlatformAssessmentRepository,
)
from app.platform.core.agentic.supervisor import policy_node
from app.platform.core.agentic.state import SupervisorState


# Minimal assessment snapshot required by meal structure engine + tests without Ayurveda questionnaire
def _default_assessment_snapshot():
    return {
        "client_context": {
            "age": 45,
            "gender": "male",
            "height_cm": 170,
            "weight_kg": 80,
            "activity_level": "moderately_active",
            "wake_time": "06:30",
            "sleep_time": "22:30",
        },
        "clinical_data": {
            "labs": {"HbA1c": 6.2, "FBS": 100},
            "anthropometry": {"bmi": 27.7, "height_cm": 170, "weight_kg": 80},
        },
        "goals": {},
    }


class TestSupervisorPolicy:
    """Pure unit tests (no LangGraph, no DB)."""

    def test_policy_force_full_pipeline(self):
        state: SupervisorState = {"user_feedback": {"force_full_pipeline": True}}
        assert policy_node(state)["pipeline_mode"] == "full"

    def test_policy_from_target_text(self):
        state: SupervisorState = {"user_feedback": {"text": "reduce my calories"}}
        assert policy_node(state)["pipeline_mode"] == "from_target"

    def test_policy_from_target_keyword_calories_in_message(self):
        state: SupervisorState = {"user_feedback": {"message": "lower calorie lunch"}}
        assert policy_node(state)["pipeline_mode"] == "from_target"

    def test_policy_from_meal_structure(self):
        state: SupervisorState = {
            "user_feedback": {"text": "change meal structure: more at dinner"}
        }
        assert policy_node(state)["pipeline_mode"] == "from_meal_structure"

    def test_policy_from_meal_structure_breakfast_keyword(self):
        state: SupervisorState = {"user_feedback": {"text": "bigger breakfast please"}}
        assert policy_node(state)["pipeline_mode"] == "from_meal_structure"

    def test_policy_existing_only(self):
        state: SupervisorState = {"user_feedback": {"text": "looks good"}}
        assert policy_node(state)["pipeline_mode"] == "existing_only"

    def test_policy_full_beats_meal_keywords_if_forced(self):
        state: SupervisorState = {
            "user_feedback": {
                "force_full_pipeline": True,
                "text": "breakfast timing",
            }
        }
        assert policy_node(state)["pipeline_mode"] == "full"


@pytest.mark.integration
class TestWeeklyPlanGenerateWeekAPI:
    """
    POST /plans/generate-week end-to-end (requires PostgreSQL + langgraph).
    """

    @staticmethod
    def _require_langgraph():
        pytest.importorskip("langgraph")

    def _create_assessment(self, platform_db: Session, client, snapshot=None, status="draft"):
        repo = PlatformAssessmentRepository(platform_db)
        return repo.create(
            {
                "client_id": client.id,
                "assessment_snapshot": snapshot or _default_assessment_snapshot(),
                "assessment_status": status,
            }
        )

    def _seed_full_plan(self, platform_client: TestClient, client_id: str, assessment_id: str):
        r = platform_client.post(
            "/api/v1/platform/plans/generate",
            json={
                "client_id": client_id,
                "assessment_id": assessment_id,
                "enable_ayurveda": False,
                "skip_recipe_llm": True,
            },
        )
        assert r.status_code == 201, r.text
        return r.json()

    def _week(
        self,
        platform_client: TestClient,
        client_id: str,
        assessment_id: str,
        feedback: dict,
    ):
        return platform_client.post(
            "/api/v1/platform/plans/generate-week",
            json={
                "client_id": client_id,
                "assessment_id": assessment_id,
                "feedback": feedback,
                "enable_ayurveda": False,
                "skip_recipe_llm": True,
            },
        )

    def test_generate_week_pipeline_mode_full(
        self, platform_client: TestClient, create_test_client, platform_db: Session
    ):
        self._require_langgraph()
        client = create_test_client(name="Weekly Full Mode")
        assessment = self._create_assessment(platform_db, client)
        self._seed_full_plan(platform_client, str(client.id), str(assessment.id))

        r2 = self._week(
            platform_client,
            str(client.id),
            str(assessment.id),
            {"force_full_pipeline": True},
        )
        assert r2.status_code == 201, r2.text
        data = r2.json()
        assert data.get("pipeline_mode") == "full"
        assert data.get("plan_id") or data.get("plan")

    def test_generate_week_pipeline_mode_from_target(
        self, platform_client: TestClient, create_test_client, platform_db: Session
    ):
        self._require_langgraph()
        client = create_test_client(name="Weekly From Target")
        assessment = self._create_assessment(platform_db, client)
        self._seed_full_plan(platform_client, str(client.id), str(assessment.id))

        r2 = self._week(
            platform_client,
            str(client.id),
            str(assessment.id),
            {"text": "I need to reduce calories"},
        )
        assert r2.status_code == 201, r2.text
        data = r2.json()
        assert data.get("pipeline_mode") == "from_target"
        assert data.get("plan_id") or data.get("plan")

    def test_generate_week_pipeline_mode_from_meal_structure(
        self, platform_client: TestClient, create_test_client, platform_db: Session
    ):
        self._require_langgraph()
        client = create_test_client(name="Weekly Meal Structure")
        assessment = self._create_assessment(platform_db, client)
        self._seed_full_plan(platform_client, str(client.id), str(assessment.id))

        r2 = self._week(
            platform_client,
            str(client.id),
            str(assessment.id),
            {"text": "adjust my meal timing and dinner"},
        )
        assert r2.status_code == 201, r2.text
        data = r2.json()
        assert data.get("pipeline_mode") == "from_meal_structure"
        assert data.get("plan_id") or data.get("plan")

    def test_generate_week_pipeline_mode_existing_only(
        self, platform_client: TestClient, create_test_client, platform_db: Session
    ):
        self._require_langgraph()
        client = create_test_client(name="Weekly Existing Only")
        assessment = self._create_assessment(platform_db, client)
        self._seed_full_plan(platform_client, str(client.id), str(assessment.id))

        r2 = self._week(
            platform_client,
            str(client.id),
            str(assessment.id),
            {},
        )
        assert r2.status_code == 201, r2.text
        data = r2.json()
        assert data.get("pipeline_mode") == "existing_only"
        assert data.get("plan_id") or data.get("plan")

    def test_generate_week_returns_plan_payload(
        self, platform_client: TestClient, create_test_client, platform_db: Session
    ):
        self._require_langgraph()
        client = create_test_client(name="Weekly Plan Payload")
        assessment = self._create_assessment(platform_db, client)
        self._seed_full_plan(platform_client, str(client.id), str(assessment.id))

        r2 = self._week(
            platform_client,
            str(client.id),
            str(assessment.id),
            {"text": "ok"},
        )
        assert r2.status_code == 201
        data = r2.json()
        if data.get("plan"):
            assert data["plan"]["client_id"] == str(client.id)
            assert data["plan"]["assessment_id"] == str(assessment.id)

    def test_generate_week_client_not_found(
        self, platform_client: TestClient, create_test_client, platform_db: Session
    ):
        self._require_langgraph()
        client = create_test_client(name="C")
        assessment = self._create_assessment(platform_db, client)
        r = platform_client.post(
            "/api/v1/platform/plans/generate-week",
            json={
                "client_id": str(uuid.uuid4()),
                "assessment_id": str(assessment.id),
                "feedback": {},
                "enable_ayurveda": False,
                "skip_recipe_llm": True,
            },
        )
        assert r.status_code == 404


class TestTargetEngineOverrideGuardrails:
    """Unit tests for target engine override validation and fallback."""

    def test_invalid_calories_target_override_ignored(self):
        from app.platform.engines.target_engine.target_engine import TargetEngine
        from app.platform.core.context import MNTContext
        from uuid import uuid4

        engine = TargetEngine()
        mnt = MNTContext(
            assessment_id=uuid4(),
            macro_constraints={},
            micro_constraints={},
            food_exclusions=[],
            rule_ids_used=[],
        )
        profile = {"height_cm": 170, "gender": "male", "activity_level": "sedentary"}
        overrides_invalid = {"calories_target": 100}

        res = engine.calculate_calories(
            profile, mnt, activity_level="sedentary", overrides=overrides_invalid
        )

        assert res["calories_target"] is not None
        assert res["calories_target"] != 100
        assert res["calories_target"] >= 800
        assert res["calculation_source"] == "ibw_based"

    def test_valid_calories_target_override_applied(self):
        from app.platform.engines.target_engine.target_engine import TargetEngine
        from app.platform.core.context import MNTContext
        from uuid import uuid4

        engine = TargetEngine()
        mnt = MNTContext(
            assessment_id=uuid4(),
            macro_constraints={},
            micro_constraints={},
            food_exclusions=[],
            rule_ids_used=[],
        )
        profile = {"height_cm": 170, "gender": "male"}
        overrides_valid = {"calories_target": 1800}

        res = engine.calculate_calories(
            profile, mnt, activity_level="sedentary", overrides=overrides_valid
        )

        assert res["calories_target"] == 1800.0
        assert res["calculation_source"] == "ibw_based"
