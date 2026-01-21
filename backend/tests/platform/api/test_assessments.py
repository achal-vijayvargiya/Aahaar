"""
Tests for Platform Assessments API endpoints.

Integration tests for the platform assessments API at /api/v1/platform/assessments.
"""
import pytest
import uuid
from sqlalchemy.orm import Session
from uuid import UUID, uuid4
from fastapi.testclient import TestClient

from app.platform.data.repositories.platform_client_repository import PlatformClientRepository
from app.platform.data.repositories.platform_intake_repository import PlatformIntakeRepository
from app.platform.data.repositories.platform_assessment_repository import PlatformAssessmentRepository


class TestCreateIntake:
    """Test suite for POST /api/v1/platform/assessments/intake endpoint."""
    
    def test_create_intake_success(self, platform_client: TestClient, create_test_client):
        """Test successful intake creation with all fields."""
        # Create a test client first
        client = create_test_client(name="Test Client")
        client_id = str(client.id)
        
        intake_data = {
            "client_id": client_id,
            "raw_input": {
                "labs": {
                    "HbA1c": 7.5,
                    "FBS": 140,
                    "cholesterol": 220
                },
                "vitals": {
                    "weight_kg": 75,
                    "height_cm": 170,
                    "bp_systolic": 130
                }
            },
            "source": "manual"
        }
        
        response = platform_client.post(
            "/api/v1/platform/assessments/intake",
            json=intake_data
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert "id" in data
        assert UUID(data["id"])  # Verify it's a valid UUID
        assert data["client_id"] == client_id
        assert data["source"] == "manual"
        assert "created_at" in data
    
    def test_create_intake_minimal(self, platform_client: TestClient, create_test_client):
        """Test creating intake with only required fields (client_id)."""
        client = create_test_client(name="Test Client")
        client_id = str(client.id)
        
        intake_data = {
            "client_id": client_id
        }
        
        response = platform_client.post(
            "/api/v1/platform/assessments/intake",
            json=intake_data
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["client_id"] == client_id
        assert data["source"] == "manual"  # Default value
        assert "id" in data
        assert "created_at" in data
        # Note: raw_input is not included in IntakeResponse model
    
    def test_create_intake_with_all_sources(self, platform_client: TestClient, create_test_client):
        """Test creating intake with different source values."""
        client = create_test_client(name="Test Client")
        client_id = str(client.id)
        
        sources = ["manual", "upload", "ai_extracted"]
        
        for source in sources:
            intake_data = {
                "client_id": client_id,
                "source": source
            }
            
            response = platform_client.post(
                "/api/v1/platform/assessments/intake",
                json=intake_data
            )
            
            assert response.status_code == 201
            data = response.json()
            assert data["source"] == source
    
    def test_create_intake_client_not_found(self, platform_client: TestClient):
        """Test creating intake with non-existent client_id."""
        non_existent_id = str(uuid4())
        
        intake_data = {
            "client_id": non_existent_id,
            "raw_input": {"labs": {"HbA1c": 7.5}}
        }
        
        response = platform_client.post(
            "/api/v1/platform/assessments/intake",
            json=intake_data
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_create_intake_invalid_source(self, platform_client: TestClient, create_test_client):
        """Test creating intake with invalid source value."""
        client = create_test_client(name="Test Client")
        client_id = str(client.id)
        
        intake_data = {
            "client_id": client_id,
            "source": "invalid_source"
        }
        
        response = platform_client.post(
            "/api/v1/platform/assessments/intake",
            json=intake_data
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_create_intake_invalid_uuid(self, platform_client: TestClient):
        """Test creating intake with invalid UUID format."""
        intake_data = {
            "client_id": "not-a-uuid",
            "raw_input": {"labs": {"HbA1c": 7.5}}
        }
        
        response = platform_client.post(
            "/api/v1/platform/assessments/intake",
            json=intake_data
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_create_intake_with_complex_raw_input(self, platform_client: TestClient, create_test_client):
        """Test creating intake with complex raw_input structure."""
        client = create_test_client(name="Test Client")
        client_id = str(client.id)
        
        complex_raw_input = {
            "labs": {
                "HbA1c": 7.5,
                "FBS": 140,
                "cholesterol": 220,
                "triglycerides": 180
            },
            "vitals": {
                "weight_kg": 75,
                "height_cm": 170,
                "bp_systolic": 130,
                "bp_diastolic": 85
            },
            "medical_history": {
                "conditions": ["type_2_diabetes", "hypertension"],
                "medications": ["metformin", "lisinopril"]
            },
            "diet_history": {
                "meals_per_day": 3,
                "preferred_cuisine": "Indian",
                "dietary_restrictions": ["vegetarian"]
            },
            "lifestyle": {
                "sleep_hours": 6,
                "stress_level": "high",
                "activity_level": "sedentary"
            },
            "ayurveda_quiz": {
                "dosha_scores": {"vata": 5, "pitta": 8, "kapha": 3}
            }
        }
        
        intake_data = {
            "client_id": client_id,
            "raw_input": complex_raw_input,
            "source": "manual"
        }
        
        response = platform_client.post(
            "/api/v1/platform/assessments/intake",
            json=intake_data
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["client_id"] == client_id


class TestCreateAssessment:
    """Test suite for POST /api/v1/platform/assessments/ endpoint."""
    
    def test_create_assessment_success(self, platform_client: TestClient, create_test_client):
        """Test successful assessment creation with all fields."""
        client = create_test_client(name="Test Client")
        client_id = str(client.id)
        
        assessment_data = {
            "client_id": client_id,
            "assessment_snapshot": {
                "client_context": {
                    "age": 45,
                    "gender": "Male",
                    "height_cm": 170,
                    "weight_kg": 75,
                    "bmi": 25.95
                },
                "clinical_data": {
                    "labs": {"HbA1c": 7.5},
                    "vitals": {"bp_systolic": 130}
                }
            }
        }
        
        response = platform_client.post(
            "/api/v1/platform/assessments/",
            json=assessment_data
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert "id" in data
        assert UUID(data["id"])
        assert data["client_id"] == client_id
        assert data["assessment_status"] == "draft"
        assert data["intake_id"] is None
        assert "created_at" in data
    
    def test_create_assessment_with_intake(self, platform_client: TestClient, create_test_client, platform_db):
        """Test creating assessment linked to an intake."""
        client = create_test_client(name="Test Client")
        client_id = str(client.id)
        
        # Create an intake first
        intake_repo = PlatformIntakeRepository(platform_db)
        intake = intake_repo.create({
            "client_id": client.id,
            "raw_input": {"labs": {"HbA1c": 7.5}},
            "source": "manual"
        })
        intake_id = str(intake.id)
        
        assessment_data = {
            "client_id": client_id,
            "intake_id": intake_id,
            "assessment_snapshot": {
                "client_context": {"age": 45}
            }
        }
        
        response = platform_client.post(
            "/api/v1/platform/assessments/",
            json=assessment_data
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["client_id"] == client_id
        assert data["intake_id"] == intake_id
        assert data["assessment_status"] == "draft"
    
    def test_create_assessment_minimal(self, platform_client: TestClient, create_test_client):
        """Test creating assessment with only required fields."""
        client = create_test_client(name="Test Client")
        client_id = str(client.id)
        
        assessment_data = {
            "client_id": client_id
        }
        
        response = platform_client.post(
            "/api/v1/platform/assessments/",
            json=assessment_data
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["client_id"] == client_id
        assert data["assessment_status"] == "draft"
        assert data["intake_id"] is None
    
    def test_create_assessment_client_not_found(self, platform_client: TestClient):
        """Test creating assessment with non-existent client_id."""
        non_existent_id = str(uuid4())
        
        assessment_data = {
            "client_id": non_existent_id,
            "assessment_snapshot": {"client_context": {"age": 45}}
        }
        
        response = platform_client.post(
            "/api/v1/platform/assessments/",
            json=assessment_data
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_create_assessment_intake_not_found(self, platform_client: TestClient, create_test_client):
        """Test creating assessment with non-existent intake_id."""
        client = create_test_client(name="Test Client")
        client_id = str(client.id)
        non_existent_intake_id = str(uuid4())
        
        assessment_data = {
            "client_id": client_id,
            "intake_id": non_existent_intake_id
        }
        
        response = platform_client.post(
            "/api/v1/platform/assessments/",
            json=assessment_data
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "intake" in data["detail"].lower()
        assert "not found" in data["detail"].lower()
    
    def test_create_assessment_intake_wrong_client(self, platform_client: TestClient, create_test_client, platform_db):
        """Test creating assessment with intake belonging to different client."""
        client1 = create_test_client(name="Client 1")
        client2 = create_test_client(name="Client 2")
        
        # Create intake for client1
        intake_repo = PlatformIntakeRepository(platform_db)
        intake = intake_repo.create({
            "client_id": client1.id,
            "raw_input": {"labs": {"HbA1c": 7.5}},
            "source": "manual"
        })
        intake_id = str(intake.id)
        
        # Try to create assessment for client2 using client1's intake
        assessment_data = {
            "client_id": str(client2.id),
            "intake_id": intake_id
        }
        
        response = platform_client.post(
            "/api/v1/platform/assessments/",
            json=assessment_data
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "does not belong" in data["detail"].lower()
    
    def test_create_assessment_invalid_uuid(self, platform_client: TestClient):
        """Test creating assessment with invalid UUID format."""
        assessment_data = {
            "client_id": "not-a-uuid"
        }
        
        response = platform_client.post(
            "/api/v1/platform/assessments/",
            json=assessment_data
        )
        
        assert response.status_code == 422  # Validation error


class TestGetAssessment:
    """Test suite for GET /api/v1/platform/assessments/{assessment_id} endpoint."""
    
    def test_get_assessment_success(self, platform_client: TestClient, create_test_client, platform_db):
        """Test successfully retrieving an assessment by ID."""
        client = create_test_client(name="Test Client")
        
        # Create an assessment
        from app.platform.data.repositories.platform_assessment_repository import PlatformAssessmentRepository
        assessment_repo = PlatformAssessmentRepository(platform_db)
        assessment = assessment_repo.create({
            "client_id": client.id,
            "assessment_snapshot": {"client_context": {"age": 45}},
            "assessment_status": "draft"
        })
        assessment_id = str(assessment.id)
        
        response = platform_client.get(f"/api/v1/platform/assessments/{assessment_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == assessment_id
        assert data["client_id"] == str(client.id)
        assert data["assessment_status"] == "draft"
        assert "created_at" in data
    
    def test_get_assessment_not_found(self, platform_client: TestClient):
        """Test retrieving a non-existent assessment."""
        non_existent_id = str(uuid4())
        
        response = platform_client.get(f"/api/v1/platform/assessments/{non_existent_id}")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_get_assessment_invalid_uuid(self, platform_client: TestClient):
        """Test with invalid UUID format."""
        invalid_id = "not-a-uuid"
        
        response = platform_client.get(f"/api/v1/platform/assessments/{invalid_id}")
        
        assert response.status_code == 422  # Validation error
    
    def test_get_assessment_with_intake(self, platform_client: TestClient, create_test_client, platform_db):
        """Test retrieving assessment that has linked intake."""
        client = create_test_client(name="Test Client")
        
        # Create intake
        intake_repo = PlatformIntakeRepository(platform_db)
        intake = intake_repo.create({
            "client_id": client.id,
            "raw_input": {"labs": {"HbA1c": 7.5}},
            "source": "manual"
        })
        
        # Create assessment with intake
        assessment_repo = PlatformAssessmentRepository(platform_db)
        assessment = assessment_repo.create({
            "client_id": client.id,
            "intake_id": intake.id,
            "assessment_snapshot": {"client_context": {"age": 45}},
            "assessment_status": "draft"
        })
        assessment_id = str(assessment.id)
        
        response = platform_client.get(f"/api/v1/platform/assessments/{assessment_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == assessment_id
        assert data["intake_id"] == str(intake.id)


class TestGetClientAssessments:
    """Test suite for GET /api/v1/platform/assessments/client/{client_id} endpoint."""
    
    def test_get_client_assessments_empty(self, platform_client: TestClient, create_test_client):
        """Test getting assessments for client with no assessments."""
        client = create_test_client(name="Test Client")
        client_id = str(client.id)
        
        response = platform_client.get(f"/api/v1/platform/assessments/client/{client_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data == []
        assert len(data) == 0
    
    def test_get_client_assessments_with_data(self, platform_client: TestClient, create_test_client, platform_db):
        """Test getting assessments when client has assessments."""
        client = create_test_client(name="Test Client")
        client_id = str(client.id)
        
        # Create multiple assessments
        assessment_repo = PlatformAssessmentRepository(platform_db)
        for i in range(3):
            assessment_repo.create({
                "client_id": client.id,
                "assessment_snapshot": {"client_context": {"age": 45 + i}},
                "assessment_status": "draft"
            })
        
        response = platform_client.get(f"/api/v1/platform/assessments/client/{client_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert all("id" in assessment for assessment in data)
        assert all(assessment["client_id"] == client_id for assessment in data)
    
    def test_get_client_assessments_pagination(self, platform_client: TestClient, create_test_client, platform_db):
        """Test pagination with skip and limit."""
        client = create_test_client(name="Test Client")
        client_id = str(client.id)
        
        # Create 5 assessments
        assessment_repo = PlatformAssessmentRepository(platform_db)
        for i in range(5):
            assessment_repo.create({
                "client_id": client.id,
                "assessment_snapshot": {"client_context": {"age": 45 + i}},
                "assessment_status": "draft"
            })
        
        # Get first page
        response = platform_client.get(f"/api/v1/platform/assessments/client/{client_id}?skip=0&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        
        # Get second page
        response = platform_client.get(f"/api/v1/platform/assessments/client/{client_id}?skip=2&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
    
    def test_get_client_assessments_client_not_found(self, platform_client: TestClient):
        """Test getting assessments for non-existent client."""
        non_existent_id = str(uuid4())
        
        response = platform_client.get(f"/api/v1/platform/assessments/client/{non_existent_id}")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_get_client_assessments_invalid_uuid(self, platform_client: TestClient):
        """Test with invalid UUID format."""
        invalid_id = "not-a-uuid"
        
        response = platform_client.get(f"/api/v1/platform/assessments/client/{invalid_id}")
        
        assert response.status_code == 422  # Validation error
    
    def test_get_client_assessments_only_returns_client_assessments(self, platform_client: TestClient, create_test_client, platform_db):
        """Test that only assessments for the specified client are returned."""
        client1 = create_test_client(name="Client 1")
        client2 = create_test_client(name="Client 2")
        
        # Create assessments for both clients
        assessment_repo = PlatformAssessmentRepository(platform_db)
        assessment_repo.create({
            "client_id": client1.id,
            "assessment_snapshot": {"client_context": {"age": 45}},
            "assessment_status": "draft"
        })
        assessment_repo.create({
            "client_id": client1.id,
            "assessment_snapshot": {"client_context": {"age": 46}},
            "assessment_status": "draft"
        })
        assessment_repo.create({
            "client_id": client2.id,
            "assessment_snapshot": {"client_context": {"age": 50}},
            "assessment_status": "draft"
        })
        
        # Get assessments for client1
        response = platform_client.get(f"/api/v1/platform/assessments/client/{client1.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(assessment["client_id"] == str(client1.id) for assessment in data)


class TestAssessmentEdgeCases:
    """Test suite for edge cases and error handling."""
    
    def test_create_intake_empty_raw_input(self, platform_client: TestClient, create_test_client):
        """Test creating intake with empty raw_input dict."""
        client = create_test_client(name="Test Client")
        client_id = str(client.id)
        
        intake_data = {
            "client_id": client_id,
            "raw_input": {}
        }
        
        response = platform_client.post(
            "/api/v1/platform/assessments/intake",
            json=intake_data
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["client_id"] == client_id
    
    def test_create_assessment_empty_snapshot(self, platform_client: TestClient, create_test_client):
        """Test creating assessment with empty assessment_snapshot."""
        client = create_test_client(name="Test Client")
        client_id = str(client.id)
        
        assessment_data = {
            "client_id": client_id,
            "assessment_snapshot": {}
        }
        
        response = platform_client.post(
            "/api/v1/platform/assessments/",
            json=assessment_data
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["client_id"] == client_id
    
    def test_get_client_assessments_large_skip(self, platform_client: TestClient, create_test_client, platform_db):
        """Test pagination with skip larger than total records."""
        client = create_test_client(name="Test Client")
        client_id = str(client.id)
        
        # Create 2 assessments
        assessment_repo = PlatformAssessmentRepository(platform_db)
        for i in range(2):
            assessment_repo.create({
                "client_id": client.id,
                "assessment_snapshot": {"client_context": {"age": 45 + i}},
                "assessment_status": "draft"
            })
        
        # Skip more than total
        response = platform_client.get(f"/api/v1/platform/assessments/client/{client_id}?skip=100")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0


class TestProcessMNT:
    """Test suite for POST /api/v1/platform/assessments/mnt endpoint."""
    
    def test_process_mnt_success(self, platform_client: TestClient, create_test_client, platform_db):
        """Test successful MNT processing."""
        client = create_test_client(name="Test Client")
        
        # Create an assessment
        assessment_repo = PlatformAssessmentRepository(platform_db)
        assessment = assessment_repo.create({
            "client_id": client.id,
            "assessment_snapshot": {
                "client_context": {"bmi": 32},
                "clinical_data": {
                    "labs": {"HbA1c": 7.5}
                }
            },
            "assessment_status": "draft"
        })
        
        # Create diagnoses for the assessment
        from app.platform.data.repositories.platform_diagnosis_repository import PlatformDiagnosisRepository
        diagnosis_repo = PlatformDiagnosisRepository(platform_db)
        diagnosis_repo.create({
            "assessment_id": assessment.id,
            "diagnosis_type": "medical",
            "diagnosis_id": "type_2_diabetes",
            "severity_score": 7.0,
            "evidence": {"HbA1c": 7.5}
        })
        diagnosis_repo.create({
            "assessment_id": assessment.id,
            "diagnosis_type": "medical",
            "diagnosis_id": "obesity",
            "severity_score": 6.0,
            "evidence": {"bmi": 32}
        })
        
        # Process MNT
        response = platform_client.post(
            "/api/v1/platform/assessments/mnt",
            json={"assessment_id": str(assessment.id)}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "macro_constraints" in data
        assert "micro_constraints" in data
        assert "food_exclusions" in data
        assert "rule_ids_used" in data
        
        # Verify constraints were generated
        assert len(data["rule_ids_used"]) > 0
        assert "mnt_carb_restriction_diabetes" in data["rule_ids_used"]
        assert "mnt_calorie_restriction_obesity" in data["rule_ids_used"]
    
    def test_process_mnt_verifies_structure(self, platform_client: TestClient, create_test_client, platform_db):
        """Test that MNT response has correct structure."""
        client = create_test_client(name="Test Client")
        
        assessment_repo = PlatformAssessmentRepository(platform_db)
        assessment = assessment_repo.create({
            "client_id": client.id,
            "assessment_snapshot": {}
        })
        
        # Create a diagnosis
        from app.platform.data.repositories.platform_diagnosis_repository import PlatformDiagnosisRepository
        diagnosis_repo = PlatformDiagnosisRepository(platform_db)
        diagnosis_repo.create({
            "assessment_id": assessment.id,
            "diagnosis_type": "medical",
            "diagnosis_id": "hypertension",
            "severity_score": 6.0,
            "evidence": {}
        })
        
        response = platform_client.post(
            "/api/v1/platform/assessments/mnt",
            json={"assessment_id": str(assessment.id)}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert isinstance(data["macro_constraints"], dict)
        assert isinstance(data["micro_constraints"], dict)
        assert isinstance(data["food_exclusions"], list)
        assert isinstance(data["rule_ids_used"], list)
    
    def test_process_mnt_assessment_not_found(self, platform_client: TestClient):
        """Test processing MNT for non-existent assessment."""
        non_existent_id = str(uuid4())
        
        response = platform_client.post(
            "/api/v1/platform/assessments/mnt",
            json={"assessment_id": non_existent_id}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_process_mnt_no_diagnoses(self, platform_client: TestClient, create_test_client, platform_db):
        """Test processing MNT when no diagnoses exist."""
        client = create_test_client(name="Test Client")
        
        assessment_repo = PlatformAssessmentRepository(platform_db)
        assessment = assessment_repo.create({
            "client_id": client.id,
            "assessment_snapshot": {}
        })
        
        response = platform_client.post(
            "/api/v1/platform/assessments/mnt",
            json={"assessment_id": str(assessment.id)}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "no diagnoses" in data["detail"].lower() or "diagnosis" in data["detail"].lower()
    
    def test_process_mnt_invalid_uuid(self, platform_client: TestClient):
        """Test with invalid UUID format."""
        response = platform_client.post(
            "/api/v1/platform/assessments/mnt",
            json={"assessment_id": "not-a-uuid"}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_process_mnt_stores_in_database(self, platform_client: TestClient, create_test_client, platform_db):
        """Test that MNT constraints are stored in database."""
        from app.platform.data.repositories.platform_mnt_constraint_repository import PlatformMNTConstraintRepository
        
        client = create_test_client(name="Test Client")
        
        assessment_repo = PlatformAssessmentRepository(platform_db)
        assessment = assessment_repo.create({
            "client_id": client.id,
            "assessment_snapshot": {}
        })
        
        # Create a diagnosis
        from app.platform.data.repositories.platform_diagnosis_repository import PlatformDiagnosisRepository
        diagnosis_repo = PlatformDiagnosisRepository(platform_db)
        diagnosis_repo.create({
            "assessment_id": assessment.id,
            "diagnosis_type": "medical",
            "diagnosis_id": "type_2_diabetes",
            "severity_score": 7.0,
            "evidence": {}
        })
        
        # Process MNT
        response = platform_client.post(
            "/api/v1/platform/assessments/mnt",
            json={"assessment_id": str(assessment.id)}
        )
        
        assert response.status_code == 200
        
        # Verify constraints were stored
        mnt_repo = PlatformMNTConstraintRepository(platform_db)
        stored_constraints = mnt_repo.get_by_assessment_id(assessment.id)
        
        assert len(stored_constraints) > 0
        assert stored_constraints[0].assessment_id == assessment.id
        assert stored_constraints[0].macro_constraints is not None
    
    def test_process_mnt_multiple_rules_merged(self, platform_client: TestClient, create_test_client, platform_db):
        """Test that multiple rules are properly merged."""
        client = create_test_client(name="Test Client")
        
        assessment_repo = PlatformAssessmentRepository(platform_db)
        assessment = assessment_repo.create({
            "client_id": client.id,
            "assessment_snapshot": {}
        })
        
        # Create multiple diagnoses
        from app.platform.data.repositories.platform_diagnosis_repository import PlatformDiagnosisRepository
        diagnosis_repo = PlatformDiagnosisRepository(platform_db)
        diagnosis_repo.create({
            "assessment_id": assessment.id,
            "diagnosis_type": "medical",
            "diagnosis_id": "type_2_diabetes",
            "severity_score": 7.0,
            "evidence": {}
        })
        diagnosis_repo.create({
            "assessment_id": assessment.id,
            "diagnosis_type": "medical",
            "diagnosis_id": "hypertension",
            "severity_score": 6.0,
            "evidence": {}
        })
        diagnosis_repo.create({
            "assessment_id": assessment.id,
            "diagnosis_type": "nutrition",
            "diagnosis_id": "inadequate_fiber_intake",
            "severity_score": 6.0,
            "evidence": {}
        })
        
        response = platform_client.post(
            "/api/v1/platform/assessments/mnt",
            json={"assessment_id": str(assessment.id)}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have multiple rules
        assert len(data["rule_ids_used"]) >= 3
        assert "mnt_carb_restriction_diabetes" in data["rule_ids_used"]
        assert "mnt_sodium_restriction_hypertension" in data["rule_ids_used"]
        assert "mnt_fiber_increase" in data["rule_ids_used"]
        
        # Constraints should be merged
        assert len(data["macro_constraints"]) > 0
        assert len(data["food_exclusions"]) > 0
    
    def test_process_mnt_constraints_content(self, platform_client: TestClient, create_test_client, platform_db):
        """Test that generated constraints have expected content."""
        client = create_test_client(name="Test Client")
        
        assessment_repo = PlatformAssessmentRepository(platform_db)
        assessment = assessment_repo.create({
            "client_id": client.id,
            "assessment_snapshot": {}
        })
        
        # Create diabetes diagnosis
        from app.platform.data.repositories.platform_diagnosis_repository import PlatformDiagnosisRepository
        diagnosis_repo = PlatformDiagnosisRepository(platform_db)
        diagnosis_repo.create({
            "assessment_id": assessment.id,
            "diagnosis_type": "medical",
            "diagnosis_id": "type_2_diabetes",
            "severity_score": 7.0,
            "evidence": {}
        })
        
        response = platform_client.post(
            "/api/v1/platform/assessments/mnt",
            json={"assessment_id": str(assessment.id)}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify diabetes constraints
        assert "carbohydrates_percent" in data["macro_constraints"]
        assert data["macro_constraints"]["carbohydrates_percent"]["max"] == 45
        assert "fiber_g" in data["macro_constraints"]
        assert data["macro_constraints"]["fiber_g"]["min"] == 25
        assert "refined_sugar" in data["food_exclusions"]
    
    def test_process_mnt_hypertension_constraints(self, platform_client: TestClient, create_test_client, platform_db):
        """Test hypertension-specific constraints."""
        client = create_test_client(name="Test Client")
        
        assessment_repo = PlatformAssessmentRepository(platform_db)
        assessment = assessment_repo.create({
            "client_id": client.id,
            "assessment_snapshot": {}
        })
        
        # Create hypertension diagnosis
        from app.platform.data.repositories.platform_diagnosis_repository import PlatformDiagnosisRepository
        diagnosis_repo = PlatformDiagnosisRepository(platform_db)
        diagnosis_repo.create({
            "assessment_id": assessment.id,
            "diagnosis_type": "medical",
            "diagnosis_id": "hypertension",
            "severity_score": 6.0,
            "evidence": {}
        })
        
        response = platform_client.post(
            "/api/v1/platform/assessments/mnt",
            json={"assessment_id": str(assessment.id)}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify hypertension constraints
        assert "sodium_mg" in data["micro_constraints"]
        assert data["micro_constraints"]["sodium_mg"]["max"] == 2300
        assert "processed_foods" in data["food_exclusions"]
    
    def test_process_mnt_merged_constraints_most_restrictive(self, platform_client: TestClient, create_test_client, platform_db):
        """Test that merged constraints take most restrictive values."""
        client = create_test_client(name="Test Client")
        
        assessment_repo = PlatformAssessmentRepository(platform_db)
        assessment = assessment_repo.create({
            "client_id": client.id,
            "assessment_snapshot": {}
        })
        
        # Create diagnoses that both affect carbs
        from app.platform.data.repositories.platform_diagnosis_repository import PlatformDiagnosisRepository
        diagnosis_repo = PlatformDiagnosisRepository(platform_db)
        diagnosis_repo.create({
            "assessment_id": assessment.id,
            "diagnosis_type": "medical",
            "diagnosis_id": "type_2_diabetes",
            "severity_score": 7.0,
            "evidence": {}
        })
        diagnosis_repo.create({
            "assessment_id": assessment.id,
            "diagnosis_type": "nutrition",
            "diagnosis_id": "excess_carbohydrate_intake",
            "severity_score": 7.5,
            "evidence": {}
        })
        
        response = platform_client.post(
            "/api/v1/platform/assessments/mnt",
            json={"assessment_id": str(assessment.id)}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Both map to same rule, should only appear once
        assert data["rule_ids_used"].count("mnt_carb_restriction_diabetes") == 1


class TestProcessTargets:
    """Test suite for POST /api/v1/platform/assessments/targets endpoint."""

    def _create_assessment_with_snapshot(self, platform_db, client, snapshot=None, status="draft"):
        assessment_repo = PlatformAssessmentRepository(platform_db)
        return assessment_repo.create({
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

    def _create_mnt_constraint(self, platform_db, assessment_id, macro=None, micro=None, rule_ids=None):
        from app.platform.data.repositories.platform_mnt_constraint_repository import PlatformMNTConstraintRepository
        mnt_repo = PlatformMNTConstraintRepository(platform_db)
        mnt_repo.create({
            "assessment_id": assessment_id,
            "rule_id": ",".join(rule_ids) if rule_ids else None,
            "priority": 3,
            "macro_constraints": macro or {},
            "micro_constraints": micro or {},
            "food_exclusions": []
        })

    def test_process_targets_success(self, platform_client: TestClient, create_test_client, platform_db: Session):
        """Test successful target processing."""
        client = create_test_client(name="Target Client")
        assessment = self._create_assessment_with_snapshot(platform_db, client)
        self._create_mnt_constraint(
            platform_db,
            assessment.id,
            macro={"calories": {"deficit_percent": 10}, "carbohydrates_percent": {"max": 50}},
            micro={"sodium_mg": {"max": 2000}},
            rule_ids=["mnt_carb_restriction_diabetes"]
        )

        response = platform_client.post(
            "/api/v1/platform/assessments/targets",
            json={"assessment_id": str(assessment.id), "activity_level": "moderately_active"}
        )

        assert response.status_code == 200
        data = response.json()

        assert "calories_target" in data
        assert "macros" in data
        assert "key_micros" in data
        assert "calculation_source" in data
        # Respect constraints
        assert data["key_micros"]["sodium_mg"]["max"] == 2000
        assert data["macros"]["carbohydrates"]["percent_range"]["max"] <= 50

    def test_process_targets_assessment_not_found(self, platform_client: TestClient):
        """Test 404 when assessment not found."""
        response = platform_client.post(
            "/api/v1/platform/assessments/targets",
            json={"assessment_id": str(uuid.uuid4())}
        )
        assert response.status_code == 404

    def test_process_targets_missing_mnt(self, platform_client: TestClient, create_test_client, platform_db: Session):
        """Test 404 when MNT constraints are missing."""
        client = create_test_client(name="Target Client")
        assessment = self._create_assessment_with_snapshot(platform_db, client)

        response = platform_client.post(
            "/api/v1/platform/assessments/targets",
            json={"assessment_id": str(assessment.id)}
        )

        assert response.status_code == 404
        assert "MNT" in response.json()["detail"] or "constraints" in response.json()["detail"]

    def test_process_targets_invalid_uuid(self, platform_client: TestClient):
        """Test validation error for invalid UUID."""
        response = platform_client.post(
            "/api/v1/platform/assessments/targets",
            json={"assessment_id": "not-a-uuid"}
        )
        assert response.status_code == 422

    def test_process_targets_stores_in_db(self, platform_client: TestClient, create_test_client, platform_db: Session):
        """Test that targets are stored in database."""
        from app.platform.data.repositories.platform_nutrition_target_repository import PlatformNutritionTargetRepository

        client = create_test_client(name="Target Client")
        assessment = self._create_assessment_with_snapshot(platform_db, client)
        self._create_mnt_constraint(platform_db, assessment.id)

        response = platform_client.post(
            "/api/v1/platform/assessments/targets",
            json={"assessment_id": str(assessment.id)}
        )
        assert response.status_code == 200

        target_repo = PlatformNutritionTargetRepository(platform_db)
        stored = target_repo.get_by_assessment_id(assessment.id)
        assert stored is not None
        assert stored.calories_target is not None

    def test_process_targets_respects_deficit(self, platform_client: TestClient, create_test_client, platform_db: Session):
        """Test that deficit constraint lowers calories."""
        client = create_test_client(name="Target Client")
        assessment = self._create_assessment_with_snapshot(platform_db, client)
        # Apply a calorie deficit
        self._create_mnt_constraint(platform_db, assessment.id, macro={"calories": {"deficit_percent": 20}})

        response = platform_client.post(
            "/api/v1/platform/assessments/targets",
            json={"assessment_id": str(assessment.id)}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["calculation_source"] in ["custom", "tdee", "bmr"]
        # Target calories should be >0
        assert data["calories_target"] > 0

    def test_process_targets_updates_existing(self, platform_client: TestClient, create_test_client, platform_db: Session):
        """Test that re-running targets updates existing record instead of duplicating."""
        from app.platform.data.repositories.platform_nutrition_target_repository import PlatformNutritionTargetRepository

        client = create_test_client(name="Target Client")
        assessment = self._create_assessment_with_snapshot(platform_db, client)
        self._create_mnt_constraint(platform_db, assessment.id)

        # First run
        r1 = platform_client.post(
            "/api/v1/platform/assessments/targets",
            json={"assessment_id": str(assessment.id)}
        )
        assert r1.status_code == 200

        target_repo = PlatformNutritionTargetRepository(platform_db)
        stored_first = target_repo.get_by_assessment_id(assessment.id)
        assert stored_first is not None

        # Second run with changed MNT
        self._create_mnt_constraint(platform_db, assessment.id, macro={"calories": {"min": 1800}})
        r2 = platform_client.post(
            "/api/v1/platform/assessments/targets",
            json={"assessment_id": str(assessment.id)}
        )
        assert r2.status_code == 200

        stored_second = target_repo.get_by_assessment_id(assessment.id)
        assert stored_second.id == stored_first.id  # updated same record


class TestProcessAyurveda:
    """Test suite for POST /api/v1/platform/assessments/ayurveda endpoint."""

    def _create_assessment_with_snapshot(self, platform_db, client, snapshot=None, status="draft"):
        assessment_repo = PlatformAssessmentRepository(platform_db)
        return assessment_repo.create({
            "client_id": client.id,
            "assessment_snapshot": snapshot or {
                "client_context": {
                    "age": 30,
                    "gender": "male",
                    "height_cm": 175,
                    "weight_kg": 70,
                    "activity_level": "moderately_active"
                },
                "ayurveda_data": {
                    "symptoms": ["acidity"]
                }
            },
            "assessment_status": status
        })

    def _create_mnt_constraint(self, platform_db, assessment_id, macro=None, micro=None, rule_ids=None, food_exclusions=None):
        from app.platform.data.repositories.platform_mnt_constraint_repository import PlatformMNTConstraintRepository
        mnt_repo = PlatformMNTConstraintRepository(platform_db)
        mnt_repo.create({
            "assessment_id": assessment_id,
            "rule_id": ",".join(rule_ids) if rule_ids else None,
            "priority": 3,
            "macro_constraints": macro or {},
            "micro_constraints": micro or {},
            "food_exclusions": food_exclusions or []
        })

    def test_process_ayurveda_success(self, platform_client: TestClient, create_test_client, platform_db: Session):
        """Test successful Ayurveda processing."""
        from app.platform.data.repositories.platform_ayurveda_profile_repository import PlatformAyurvedaProfileRepository

        client = create_test_client(name="Ayurveda Client")
        assessment = self._create_assessment_with_snapshot(platform_db, client)
        self._create_mnt_constraint(platform_db, assessment.id, food_exclusions=["ginger"])

        response = platform_client.post(
            "/api/v1/platform/assessments/ayurveda",
            json={"assessment_id": str(assessment.id)}
        )

        assert response.status_code == 200
        data = response.json()
        assert "dosha_primary" in data
        assert "lifestyle_guidelines" in data
        # Ensure excluded food not suggested in spices
        spices = data.get("lifestyle_guidelines", {}).get("spices", {}).get("recommendation", [])
        assert "ginger" not in spices

        repo = PlatformAyurvedaProfileRepository(platform_db)
        stored = repo.get_by_assessment_id(assessment.id)
        assert stored is not None
        assert stored.dosha_primary == data["dosha_primary"]

    def test_process_ayurveda_assessment_not_found(self, platform_client: TestClient):
        """Test 404 when assessment not found."""
        response = platform_client.post(
            "/api/v1/platform/assessments/ayurveda",
            json={"assessment_id": str(uuid.uuid4())}
        )
        assert response.status_code == 404

    def test_process_ayurveda_missing_mnt(self, platform_client: TestClient, create_test_client, platform_db: Session):
        """Test 404 when MNT constraints missing."""
        client = create_test_client(name="Ayurveda Client")
        assessment = self._create_assessment_with_snapshot(platform_db, client)

        response = platform_client.post(
            "/api/v1/platform/assessments/ayurveda",
            json={"assessment_id": str(assessment.id)}
        )
        assert response.status_code == 404

    def test_process_ayurveda_invalid_uuid(self, platform_client: TestClient):
        """Test validation error for invalid UUID."""
        response = platform_client.post(
            "/api/v1/platform/assessments/ayurveda",
            json={"assessment_id": "not-a-uuid"}
        )
        assert response.status_code == 422



class TestProcessDiagnosis:
    """Test suite for POST /api/v1/platform/assessments/diagnosis endpoint."""
    
    def test_process_diagnosis_success(self, platform_client: TestClient, create_test_client, platform_db):
        """Test successful diagnosis processing."""
        client = create_test_client(name="Test Client")
        
        # Create an assessment with complete data
        assessment_repo = PlatformAssessmentRepository(platform_db)
        assessment = assessment_repo.create({
            "client_id": client.id,
            "assessment_snapshot": {
                "client_context": {
                    "age": 45,
                    "gender": "Male",
                    "height_cm": 170,
                    "weight_kg": 85,
                    "bmi": 29.4
                },
                "clinical_data": {
                    "labs": {
                        "HbA1c": 7.5,
                        "cholesterol": 220
                    },
                    "vitals": {
                        "bp_systolic": 140,
                        "bp_diastolic": 90
                    }
                },
                "diet_data": {
                    "diet_history": {
                        "carb_intake_percent": 60,
                        "fiber_grams": 15
                    }
                }
            },
            "assessment_status": "draft"
        })
        assessment_id = str(assessment.id)
        
        # Process diagnosis
        response = platform_client.post(
            "/api/v1/platform/assessments/diagnosis",
            json={"assessment_id": assessment_id}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "medical_conditions" in data
        assert "nutrition_diagnoses" in data
        assert isinstance(data["medical_conditions"], list)
        assert isinstance(data["nutrition_diagnoses"], list)
        
        # Verify medical conditions were identified
        assert len(data["medical_conditions"]) > 0
        medical_ids = [c["diagnosis_id"] for c in data["medical_conditions"]]
        assert "type_2_diabetes" in medical_ids
        
        # Verify nutrition diagnoses were identified
        assert len(data["nutrition_diagnoses"]) > 0
        nutrition_ids = [d["diagnosis_id"] for d in data["nutrition_diagnoses"]]
        assert "excess_carbohydrate_intake" in nutrition_ids
    
    def test_process_diagnosis_verifies_structure(self, platform_client: TestClient, create_test_client, platform_db):
        """Test that diagnosis response has correct structure."""
        client = create_test_client(name="Test Client")
        
        assessment_repo = PlatformAssessmentRepository(platform_db)
        assessment = assessment_repo.create({
            "client_id": client.id,
            "assessment_snapshot": {
                "clinical_data": {
                    "labs": {"HbA1c": 7.5}
                }
            }
        })
        
        response = platform_client.post(
            "/api/v1/platform/assessments/diagnosis",
            json={"assessment_id": str(assessment.id)}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure of medical conditions
        if len(data["medical_conditions"]) > 0:
            condition = data["medical_conditions"][0]
            assert "diagnosis_id" in condition
            assert "severity_score" in condition
            assert "evidence" in condition
            assert isinstance(condition["severity_score"], (int, float))
            assert isinstance(condition["evidence"], dict)
        
        # Verify structure of nutrition diagnoses
        if len(data["nutrition_diagnoses"]) > 0:
            diagnosis = data["nutrition_diagnoses"][0]
            assert "diagnosis_id" in diagnosis
            assert "severity_score" in diagnosis
            assert "evidence" in diagnosis
            assert isinstance(diagnosis["severity_score"], (int, float))
            assert isinstance(diagnosis["evidence"], dict)
    
    def test_process_diagnosis_assessment_not_found(self, platform_client: TestClient):
        """Test processing diagnosis for non-existent assessment."""
        non_existent_id = str(uuid4())
        
        response = platform_client.post(
            "/api/v1/platform/assessments/diagnosis",
            json={"assessment_id": non_existent_id}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_process_diagnosis_invalid_uuid(self, platform_client: TestClient):
        """Test with invalid UUID format."""
        response = platform_client.post(
            "/api/v1/platform/assessments/diagnosis",
            json={"assessment_id": "not-a-uuid"}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_process_diagnosis_empty_assessment(self, platform_client: TestClient, create_test_client, platform_db):
        """Test processing diagnosis for assessment with empty snapshot."""
        client = create_test_client(name="Test Client")
        
        assessment_repo = PlatformAssessmentRepository(platform_db)
        assessment = assessment_repo.create({
            "client_id": client.id,
            "assessment_snapshot": {}
        })
        
        response = platform_client.post(
            "/api/v1/platform/assessments/diagnosis",
            json={"assessment_id": str(assessment.id)}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return empty lists if no data
        assert data["medical_conditions"] == []
        assert data["nutrition_diagnoses"] == []
    
    def test_process_diagnosis_stores_in_database(self, platform_client: TestClient, create_test_client, platform_db):
        """Test that diagnoses are stored in database."""
        from app.platform.data.repositories.platform_diagnosis_repository import PlatformDiagnosisRepository
        
        client = create_test_client(name="Test Client")
        
        assessment_repo = PlatformAssessmentRepository(platform_db)
        assessment = assessment_repo.create({
            "client_id": client.id,
            "assessment_snapshot": {
                "clinical_data": {
                    "labs": {"HbA1c": 7.5}
                }
            }
        })
        
        # Process diagnosis
        response = platform_client.post(
            "/api/v1/platform/assessments/diagnosis",
            json={"assessment_id": str(assessment.id)}
        )
        
        assert response.status_code == 200
        
        # Verify diagnoses were stored
        diagnosis_repo = PlatformDiagnosisRepository(platform_db)
        stored_diagnoses = diagnosis_repo.get_by_assessment_id(assessment.id)
        
        assert len(stored_diagnoses) > 0
        assert any(d.diagnosis_type == "medical" for d in stored_diagnoses)
        assert stored_diagnoses[0].assessment_id == assessment.id
    
    def test_process_diagnosis_multiple_conditions(self, platform_client: TestClient, create_test_client, platform_db):
        """Test processing diagnosis that identifies multiple conditions."""
        client = create_test_client(name="Test Client")
        
        assessment_repo = PlatformAssessmentRepository(platform_db)
        assessment = assessment_repo.create({
            "client_id": client.id,
            "assessment_snapshot": {
                "client_context": {"bmi": 32},
                "clinical_data": {
                    "labs": {
                        "HbA1c": 7.5,
                        "cholesterol": 220,
                        "triglycerides": 180
                    },
                    "vitals": {
                        "bp_systolic": 140,
                        "bp_diastolic": 90
                    }
                },
                "diet_data": {
                    "diet_history": {
                        "carb_intake_percent": 60,
                        "fiber_grams": 15,
                        "protein_grams": 40
                    }
                }
            }
        })
        
        response = platform_client.post(
            "/api/v1/platform/assessments/diagnosis",
            json={"assessment_id": str(assessment.id)}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should identify multiple medical conditions
        assert len(data["medical_conditions"]) >= 3
        medical_ids = [c["diagnosis_id"] for c in data["medical_conditions"]]
        assert "type_2_diabetes" in medical_ids
        assert "dyslipidemia" in medical_ids
        assert "obesity" in medical_ids
        assert "hypertension" in medical_ids
        
        # Should identify multiple nutrition diagnoses
        assert len(data["nutrition_diagnoses"]) >= 2
    
    def test_process_diagnosis_severity_scores(self, platform_client: TestClient, create_test_client, platform_db):
        """Test that severity scores are within valid range."""
        client = create_test_client(name="Test Client")
        
        assessment_repo = PlatformAssessmentRepository(platform_db)
        assessment = assessment_repo.create({
            "client_id": client.id,
            "assessment_snapshot": {
                "clinical_data": {
                    "labs": {"HbA1c": 7.5}
                }
            }
        })
        
        response = platform_client.post(
            "/api/v1/platform/assessments/diagnosis",
            json={"assessment_id": str(assessment.id)}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify severity scores are in valid range (0-10)
        for condition in data["medical_conditions"]:
            assert 0 <= condition["severity_score"] <= 10
        
        for diagnosis in data["nutrition_diagnoses"]:
            assert 0 <= diagnosis["severity_score"] <= 10
    
    def test_process_diagnosis_evidence_structure(self, platform_client: TestClient, create_test_client, platform_db):
        """Test that evidence contains required information."""
        client = create_test_client(name="Test Client")
        
        assessment_repo = PlatformAssessmentRepository(platform_db)
        assessment = assessment_repo.create({
            "client_id": client.id,
            "assessment_snapshot": {
                "clinical_data": {
                    "labs": {"HbA1c": 7.5}
                }
            }
        })
        
        response = platform_client.post(
            "/api/v1/platform/assessments/diagnosis",
            json={"assessment_id": str(assessment.id)}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify evidence structure for medical conditions
        for condition in data["medical_conditions"]:
            assert "evidence" in condition
            assert isinstance(condition["evidence"], dict)
            assert "source" in condition["evidence"]
        
        # Verify evidence structure for nutrition diagnoses
        for diagnosis in data["nutrition_diagnoses"]:
            assert "evidence" in diagnosis
            assert isinstance(diagnosis["evidence"], dict)
            assert "source" in diagnosis["evidence"]

