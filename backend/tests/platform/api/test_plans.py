"""
Integration tests for plans generation endpoint.
"""
import uuid
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.platform.data.repositories.platform_assessment_repository import PlatformAssessmentRepository
from app.platform.data.repositories.platform_mnt_constraint_repository import PlatformMNTConstraintRepository
from app.platform.data.repositories.platform_nutrition_target_repository import PlatformNutritionTargetRepository


class TestGeneratePlan:
    def _create_assessment(self, platform_db: Session, client, snapshot=None, status="draft"):
        repo = PlatformAssessmentRepository(platform_db)
        return repo.create({
            "client_id": client.id,
            "assessment_snapshot": snapshot or {
                "client_context": {
                    "age": 30,
                    "gender": "male",
                    "height_cm": 175,
                    "weight_kg": 70
                }
            },
            "assessment_status": status
        })

    def test_generate_plan_success(self, platform_client: TestClient, create_test_client, platform_db: Session):
        """Happy path generates a plan and stores it."""
        client = create_test_client(name="Plan Client")
        assessment = self._create_assessment(platform_db, client)

        response = platform_client.post(
            "/api/v1/platform/plans/generate",
            json={
                "client_id": str(client.id),
                "assessment_id": str(assessment.id)
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert "meal_plan" in data
        assert data["client_id"] == str(client.id)
        assert data["assessment_id"] == str(assessment.id)
        assert "constraints_snapshot" in data

    def test_generate_plan_assessment_not_found(self, platform_client: TestClient, create_test_client):
        client = create_test_client(name="Plan Client")
        response = platform_client.post(
            "/api/v1/platform/plans/generate",
            json={
                "client_id": str(client.id),
                "assessment_id": str(uuid.uuid4())
            }
        )
        assert response.status_code == 404

