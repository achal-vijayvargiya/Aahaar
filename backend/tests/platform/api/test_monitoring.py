"""
Integration tests for Monitoring API.
"""
import uuid
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.platform.data.repositories.platform_diet_plan_repository import PlatformDietPlanRepository
from app.platform.data.repositories.platform_assessment_repository import PlatformAssessmentRepository
from app.platform.data.repositories.platform_mnt_constraint_repository import PlatformMNTConstraintRepository
from app.platform.data.repositories.platform_nutrition_target_repository import PlatformNutritionTargetRepository
from app.platform.data.repositories.platform_diagnosis_repository import PlatformDiagnosisRepository


def setup_assessment_with_plan(platform_db: Session, client, plan_repo: PlatformDietPlanRepository):
    assessment_repo = PlatformAssessmentRepository(platform_db)
    assessment = assessment_repo.create({
        "client_id": client.id,
        "assessment_snapshot": {"client_context": {"age": 30}},
        "assessment_status": "draft"
    })

    # Minimal diagnosis/MNT/target to allow plan creation
    diagnosis_repo = PlatformDiagnosisRepository(platform_db)
    diagnosis_repo.create({
        "assessment_id": assessment.id,
        "diagnosis_type": "medical",
        "diagnosis_id": "type_2_diabetes",
        "severity_score": 7.0,
        "evidence": {}
    })

    mnt_repo = PlatformMNTConstraintRepository(platform_db)
    mnt_repo.create({
        "assessment_id": assessment.id,
        "rule_id": "mnt_carb_restriction_diabetes",
        "priority": 3,
        "macro_constraints": {"carbohydrates_percent": {"max": 50}},
        "micro_constraints": {"sodium_mg": {"max": 2000}},
        "food_exclusions": []
    })

    target_repo = PlatformNutritionTargetRepository(platform_db)
    target_repo.create({
        "assessment_id": assessment.id,
        "calories_target": 1800,
        "macros": {"carbohydrates": {"percent_range": {"max": 50}}},
        "key_micros": {"sodium_mg": {"max": 2000}},
        "calculation_source": "tdee"
    })

    plan = plan_repo.create({
        "client_id": client.id,
        "assessment_id": assessment.id,
        "plan_version": 1,
        "status": "active",
        "meal_plan": {"meals": []},
        "explanations": {},
        "constraints_snapshot": {},
    })
    return assessment, plan


class TestMonitoringAPI:
    def test_create_and_get_records(self, platform_client: TestClient, create_test_client, platform_db: Session):
        plan_repo = PlatformDietPlanRepository(platform_db)
        client = create_test_client(name="Monitor Client")
        _, plan = setup_assessment_with_plan(platform_db, client, plan_repo)

        # Create record
        resp = platform_client.post(
            "/api/v1/platform/monitoring",
            json={
                "client_id": str(client.id),
                "plan_id": str(plan.id),
                "metric_type": "vitals",
                "metric_value": {"bp_systolic": 152, "bp_diastolic": 96}
            }
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["reassess_recommended"] is True

        # List by plan with filter
        resp2 = platform_client.get(
            f"/api/v1/platform/monitoring/plan/{plan.id}?metric_type=vitals"
        )
        assert resp2.status_code == 200
        records = resp2.json()
        assert len(records) == 1
        assert records[0]["metric_type"] == "vitals"

        # List by client with date range
        start = (datetime.utcnow() - timedelta(days=1)).isoformat()
        end = (datetime.utcnow() + timedelta(days=1)).isoformat()
        resp3 = platform_client.get(
            f"/api/v1/platform/monitoring/client/{client.id}?start={start}&end={end}"
        )
        assert resp3.status_code == 200
        records_client = resp3.json()
        assert len(records_client) == 1

    def test_delete_record(self, platform_client: TestClient, create_test_client, platform_db: Session):
        plan_repo = PlatformDietPlanRepository(platform_db)
        client = create_test_client(name="Monitor Client")
        _, plan = setup_assessment_with_plan(platform_db, client, plan_repo)

        resp = platform_client.post(
            "/api/v1/platform/monitoring",
            json={
                "client_id": str(client.id),
                "plan_id": str(plan.id),
                "metric_type": "adherence",
                "metric_value": {"compliance_percent": 85}
            }
        )
        assert resp.status_code == 201
        rec_id = resp.json()["id"]

        del_resp = platform_client.delete(f"/api/v1/platform/monitoring/{rec_id}")
        assert del_resp.status_code == 204

        del_again = platform_client.delete(f"/api/v1/platform/monitoring/{rec_id}")
        assert del_again.status_code == 404

    def test_invalid_metric_type(self, platform_client: TestClient, create_test_client, platform_db: Session):
        plan_repo = PlatformDietPlanRepository(platform_db)
        client = create_test_client(name="Monitor Client")
        _, plan = setup_assessment_with_plan(platform_db, client, plan_repo)

        resp = platform_client.post(
            "/api/v1/platform/monitoring",
            json={
                "client_id": str(client.id),
                "plan_id": str(plan.id),
                "metric_type": "unknown",
                "metric_value": {}
            }
        )
        assert resp.status_code == 400

