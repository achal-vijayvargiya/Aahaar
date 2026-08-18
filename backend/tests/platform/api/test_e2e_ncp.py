"""
End-to-end tests for the platform NCP pipeline.

Covers multiple clients going through:
Client -> Assessment -> Orchestrated Plan Generation -> Monitoring.

Also includes output quality assertions that validate the actual content of
generated plans, not just HTTP status codes.
"""
from uuid import uuid4
from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


class TestEndToEndNCP:
    def _create_assessment_via_api(self, platform_client: TestClient, client_id: str):
        payload = {
            "client_id": client_id,
            "assessment_snapshot": {
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
                    "labs": {"HbA1c": 7.5, "FBS": 140, "cholesterol": 220, "triglycerides": 180},
                    "anthropometry": {"bmi": 27.7},
                },
                "diet_data": {
                    "diet_history": {
                        "carb_intake_percent": 60,
                        "fiber_g": 18,
                        "calorie_intake": 2500,
                        "protein_g_per_kg": 0.7,
                    }
                },
            },
        }
        resp = platform_client.post(
            "/api/v1/platform/assessments/",
            json=payload,
        )
        assert resp.status_code == 201
        return resp.json()["id"]

    def test_end_to_end_two_clients_independent_flows(
        self,
        platform_client: TestClient,
        create_test_client,
        platform_db: Session,
    ):
        # Create two distinct clients
        client_a = create_test_client(name="Client A")
        client_b = create_test_client(name="Client B")

        # Create assessments for both clients
        assessment_a_id = self._create_assessment_via_api(platform_client, str(client_a.id))
        assessment_b_id = self._create_assessment_via_api(platform_client, str(client_b.id))

        # Generate plans for both clients (full orchestrated pipeline, Ayurveda disabled
        # because tests don't supply the questionnaire data)
        # skip_recipe_llm: full pipeline otherwise calls OpenRouter once per meal × 7 days
        # (this test would appear "stuck" for many minutes).
        resp_plan_a1 = platform_client.post(
            "/api/v1/platform/plans/generate",
            json={
                "client_id": str(client_a.id),
                "assessment_id": assessment_a_id,
                "client_preferences": {"dislikes": ["fried"]},
                "enable_ayurveda": False,
                "skip_recipe_llm": True,
            },
        )
        assert resp_plan_a1.status_code == 201
        plan_a1 = resp_plan_a1.json()

        resp_plan_b1 = platform_client.post(
            "/api/v1/platform/plans/generate",
            json={
                "client_id": str(client_b.id),
                "assessment_id": assessment_b_id,
                "enable_ayurveda": False,
                "skip_recipe_llm": True,
            },
        )
        assert resp_plan_b1.status_code == 201
        plan_b1 = resp_plan_b1.json()

        # Ensure each client has its own plan and they are not mixed
        assert plan_a1["client_id"] == str(client_a.id)
        assert plan_b1["client_id"] == str(client_b.id)
        assert plan_a1["assessment_id"] == assessment_a_id
        assert plan_b1["assessment_id"] == assessment_b_id
        assert plan_a1["id"] != plan_b1["id"]

        # Generate a second plan for client A (should bump version)
        resp_plan_a2 = platform_client.post(
            "/api/v1/platform/plans/generate",
            json={
                "client_id": str(client_a.id),
                "assessment_id": assessment_a_id,
                "enable_ayurveda": False,
                "skip_recipe_llm": True,
            },
        )
        assert resp_plan_a2.status_code == 201
        plan_a2 = resp_plan_a2.json()
        assert plan_a2["plan_version"] == plan_a1["plan_version"] + 1

        # Fetch all plans for client A
        resp_client_plans_a = platform_client.get(
            f"/api/v1/platform/plans/client/{client_a.id}"
        )
        assert resp_client_plans_a.status_code == 200
        plans_a = resp_client_plans_a.json()
        assert len(plans_a) >= 2

        # Active plan for client A should be the latest active
        resp_active_a = platform_client.get(
            f"/api/v1/platform/plans/client/{client_a.id}/active"
        )
        assert resp_active_a.status_code == 200
        active_a = resp_active_a.json()
        assert active_a["id"] == plan_a2["id"]

        # Add monitoring records for both clients/plans
        for plan in (plan_a2, plan_b1):
            resp_mon = platform_client.post(
                "/api/v1/platform/monitoring",
                json={
                    "client_id": plan["client_id"],
                    "plan_id": plan["id"],
                    "metric_type": "vitals",
                    "metric_value": {"bp_systolic": 130, "bp_diastolic": 85},
                },
            )
            assert resp_mon.status_code == 201

        # Verify monitoring listing is scoped correctly per client
        start = (datetime.utcnow() - timedelta(days=1)).isoformat()
        end = (datetime.utcnow() + timedelta(days=1)).isoformat()

        resp_mon_a = platform_client.get(
            f"/api/v1/platform/monitoring/client/{client_a.id}?start={start}&end={end}"
        )
        resp_mon_b = platform_client.get(
            f"/api/v1/platform/monitoring/client/{client_b.id}?start={start}&end={end}"
        )
        assert resp_mon_a.status_code == 200
        assert resp_mon_b.status_code == 200
        records_a = resp_mon_a.json()
        records_b = resp_mon_b.json()
        assert all(rec["client_id"] == str(client_a.id) for rec in records_a)
        assert all(rec["client_id"] == str(client_b.id) for rec in records_b)

    def test_diabetic_plan_output_quality(
        self,
        platform_client: TestClient,
        create_test_client,
        platform_db: Session,
    ):
        """
        Validates the actual content of a generated plan for a diabetic client.

        Checks:
        - meal_plan structure: category_wise_foods present and non-empty
        - seven_day_plan: has exactly 7 days
        - Each day has positive calorie totals within physiological bounds
        - Recipe generation summary recorded in explanations
        - No food marked contraindicated for diabetes appears in category_wise_foods
        - Plan version is 1 for a new client's first plan
        """
        client = create_test_client(name="Diabetic Quality Client")

        # Diabetic profile: HbA1c 8.0 triggers MNT diabetic rules
        resp_assessment = platform_client.post(
            "/api/v1/platform/assessments/",
            json={
                "client_id": str(client.id),
                "assessment_snapshot": {
                    "client_context": {
                        "age": 52,
                        "gender": "female",
                        "height_cm": 160,
                        "weight_kg": 78,
                        "activity_level": "sedentary",
                        "wake_time": "07:00",
                        "sleep_time": "22:00",
                    },
                    "clinical_data": {
                        "labs": {"HbA1c": 8.0, "FBS": 160},
                        "anthropometry": {"bmi": 30.5, "height_cm": 160, "weight_kg": 78},
                    },
                },
            },
        )
        assert resp_assessment.status_code == 201
        assessment_id = resp_assessment.json()["id"]

        resp_plan = platform_client.post(
            "/api/v1/platform/plans/generate",
            json={
                "client_id": str(client.id),
                "assessment_id": assessment_id,
                "enable_ayurveda": False,
                "skip_recipe_llm": True,
            },
        )
        assert resp_plan.status_code == 201
        plan = resp_plan.json()

        # --- Basic identity ---
        assert plan["client_id"] == str(client.id)
        assert plan["plan_version"] == 1

        # --- meal_plan must be a non-empty dict ---
        meal_plan = plan.get("meal_plan")
        assert isinstance(meal_plan, dict), "meal_plan must be a dict"
        assert len(meal_plan) > 0, "meal_plan must not be empty"

        # --- category_wise_foods: at least one category with foods ---
        category_wise_foods = meal_plan.get("category_wise_foods", {})
        assert isinstance(category_wise_foods, dict), "category_wise_foods must be a dict"
        assert len(category_wise_foods) > 0, "category_wise_foods must have at least one exchange category"

        non_empty_categories = [cat for cat, foods in category_wise_foods.items() if foods]
        assert len(non_empty_categories) > 0, (
            f"All exchange categories are empty. Categories: {list(category_wise_foods.keys())}"
        )

        # --- No contraindicated food should appear for diabetes ---
        for category, foods in category_wise_foods.items():
            for food in foods:
                compat_levels = food.get("compatibility_levels", {})
                for condition, level in compat_levels.items():
                    assert level != "contraindicated", (
                        f"Food '{food.get('food_id')}' in category '{category}' is contraindicated "
                        f"for condition '{condition}' but was included in the plan"
                    )

        # --- seven_day_plan: 7 days with meals and positive calories ---
        seven_day_plan = meal_plan.get("seven_day_plan", {})
        assert isinstance(seven_day_plan, dict), "seven_day_plan must be a dict"

        days = seven_day_plan.get("days", {})
        assert len(days) == 7, f"Expected 7 days in plan, got {len(days)}"

        for day_key, day_data in days.items():
            daily_totals = day_data.get("daily_totals", {})
            calories = daily_totals.get("calories", 0)
            assert calories > 0, f"{day_key} daily_totals.calories is 0"
            assert 600 <= calories <= 5000, (
                f"{day_key} calories {calories} kcal outside physiological range [600, 5000]"
            )
            meals = day_data.get("meals", {})
            assert len(meals) > 0, f"{day_key} has no meals"

        # --- explanations: recipe_generation summary present ---
        explanations = plan.get("explanations") or {}
        recipe_gen = explanations.get("recipe_generation", {})
        assert recipe_gen.get("total_meals", 0) > 0, (
            "explanations.recipe_generation.total_meals must be > 0"
        )
        assert recipe_gen.get("recipes_generated") is True or recipe_gen.get(
            "recipe_llm_skipped"
        ) is True, (
            "expected LLM recipes or skip_recipe_llm marker in explanations.recipe_generation"
        )

        # --- seven_day_plan summary: successful recipes recorded ---
        summary = seven_day_plan.get("summary", {})
        assert summary.get("total_meals", 0) > 0, "seven_day_plan.summary.total_meals must be > 0"


