"""
End-to-end tests for the platform NCP pipeline.

Covers multiple clients going through:
Client -> Assessment -> Orchestrated Plan Generation -> Monitoring.
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

        # Generate plans for both clients (full orchestrated pipeline)
        resp_plan_a1 = platform_client.post(
            "/api/v1/platform/plans/generate",
            json={
                "client_id": str(client_a.id),
                "assessment_id": assessment_a_id,
                "client_preferences": {"dislikes": ["fried"]},
            },
        )
        assert resp_plan_a1.status_code == 201
        plan_a1 = resp_plan_a1.json()

        resp_plan_b1 = platform_client.post(
            "/api/v1/platform/plans/generate",
            json={
                "client_id": str(client_b.id),
                "assessment_id": assessment_b_id,
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


