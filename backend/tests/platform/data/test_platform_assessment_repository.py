"""
Tests for Platform Assessment Repository.

Unit tests for the data layer - testing repository methods in isolation.
"""
import pytest
from uuid import UUID, uuid4
from sqlalchemy.orm import Session

from app.platform.data.repositories.platform_assessment_repository import PlatformAssessmentRepository
from app.platform.data.models.platform_assessment import PlatformAssessment
from app.platform.data.repositories.platform_client_repository import PlatformClientRepository
from app.platform.data.repositories.platform_intake_repository import PlatformIntakeRepository


class TestPlatformAssessmentRepository:
    """Test suite for PlatformAssessmentRepository."""
    
    def test_create_assessment(self, platform_db: Session, create_test_client):
        """Test creating a new assessment."""
        repository = PlatformAssessmentRepository(platform_db)
        client = create_test_client(name="Test Client")
        
        assessment_data = {
            "client_id": client.id,
            "assessment_snapshot": {
                "client_context": {"age": 45},
                "clinical_data": {"labs": {"HbA1c": 7.5}}
            },
            "assessment_status": "draft"
        }
        
        assessment = repository.create(assessment_data)
        
        assert assessment is not None
        assert assessment.id is not None
        assert isinstance(assessment.id, UUID)
        assert assessment.client_id == client.id
        assert assessment.assessment_status == "draft"
        assert assessment.intake_id is None
        assert assessment.assessment_snapshot == assessment_data["assessment_snapshot"]
        assert assessment.created_at is not None
    
    def test_create_assessment_with_intake(self, platform_db: Session, create_test_client):
        """Test creating an assessment linked to an intake."""
        repository = PlatformAssessmentRepository(platform_db)
        intake_repository = PlatformIntakeRepository(platform_db)
        client = create_test_client(name="Test Client")
        
        # Create an intake
        intake = intake_repository.create({
            "client_id": client.id,
            "raw_input": {"labs": {"HbA1c": 7.5}},
            "source": "manual"
        })
        
        # Create assessment with intake
        assessment_data = {
            "client_id": client.id,
            "intake_id": intake.id,
            "assessment_snapshot": {"client_context": {"age": 45}},
            "assessment_status": "draft"
        }
        
        assessment = repository.create(assessment_data)
        
        assert assessment is not None
        assert assessment.intake_id == intake.id
        assert assessment.client_id == client.id
    
    def test_create_assessment_minimal(self, platform_db: Session, create_test_client):
        """Test creating an assessment with only required fields."""
        repository = PlatformAssessmentRepository(platform_db)
        client = create_test_client(name="Test Client")
        
        assessment_data = {
            "client_id": client.id
        }
        
        assessment = repository.create(assessment_data)
        
        assert assessment is not None
        assert assessment.id is not None
        assert assessment.client_id == client.id
        assert assessment.assessment_snapshot is None
        assert assessment.assessment_status is None
    
    def test_get_by_id(self, platform_db: Session, create_test_client):
        """Test retrieving an assessment by ID."""
        repository = PlatformAssessmentRepository(platform_db)
        client = create_test_client(name="Test Client")
        
        # Create an assessment
        created_assessment = repository.create({
            "client_id": client.id,
            "assessment_snapshot": {"client_context": {"age": 45}},
            "assessment_status": "draft"
        })
        assessment_id = created_assessment.id
        
        # Retrieve by ID
        assessment = repository.get_by_id(assessment_id)
        
        assert assessment is not None
        assert assessment.id == assessment_id
        assert assessment.client_id == client.id
        assert assessment.assessment_status == "draft"
    
    def test_get_by_id_not_found(self, platform_db: Session):
        """Test retrieving a non-existent assessment by ID."""
        repository = PlatformAssessmentRepository(platform_db)
        
        non_existent_id = uuid4()
        assessment = repository.get_by_id(non_existent_id)
        
        assert assessment is None
    
    def test_get_by_client_id(self, platform_db: Session, create_test_client):
        """Test retrieving assessments by client ID."""
        repository = PlatformAssessmentRepository(platform_db)
        client = create_test_client(name="Test Client")
        
        # Create multiple assessments for the client
        for i in range(3):
            repository.create({
                "client_id": client.id,
                "assessment_snapshot": {"client_context": {"age": 45 + i}},
                "assessment_status": "draft"
            })
        
        # Retrieve all assessments for client
        assessments = repository.get_by_client_id(client.id)
        
        assert len(assessments) == 3
        assert all(assessment.client_id == client.id for assessment in assessments)
    
    def test_get_by_client_id_empty(self, platform_db: Session, create_test_client):
        """Test getting assessments for client with no assessments."""
        repository = PlatformAssessmentRepository(platform_db)
        client = create_test_client(name="Test Client")
        
        assessments = repository.get_by_client_id(client.id)
        
        assert assessments == []
        assert len(assessments) == 0
    
    def test_get_by_status(self, platform_db: Session, create_test_client):
        """Test retrieving assessments by status."""
        repository = PlatformAssessmentRepository(platform_db)
        client = create_test_client(name="Test Client")
        
        # Create assessments with different statuses
        repository.create({
            "client_id": client.id,
            "assessment_status": "draft"
        })
        repository.create({
            "client_id": client.id,
            "assessment_status": "draft"
        })
        repository.create({
            "client_id": client.id,
            "assessment_status": "finalized"
        })
        
        # Get draft assessments
        draft_assessments = repository.get_by_status("draft")
        assert len(draft_assessments) == 2
        assert all(a.assessment_status == "draft" for a in draft_assessments)
        
        # Get finalized assessments
        finalized_assessments = repository.get_by_status("finalized")
        assert len(finalized_assessments) == 1
        assert all(a.assessment_status == "finalized" for a in finalized_assessments)
    
    def test_get_all_empty(self, platform_db: Session):
        """Test getting all assessments from empty database."""
        repository = PlatformAssessmentRepository(platform_db)
        
        assessments = repository.get_all()
        
        assert assessments == []
        assert len(assessments) == 0
    
    def test_get_all_pagination(self, platform_db: Session, create_test_client):
        """Test getting all assessments with pagination."""
        repository = PlatformAssessmentRepository(platform_db)
        client = create_test_client(name="Test Client")
        
        # Create multiple assessments
        for i in range(5):
            repository.create({
                "client_id": client.id,
                "assessment_snapshot": {"client_context": {"age": 45 + i}},
                "assessment_status": "draft"
            })
        
        # Test pagination
        assessments_page1 = repository.get_all(skip=0, limit=2)
        assert len(assessments_page1) == 2
        
        assessments_page2 = repository.get_all(skip=2, limit=2)
        assert len(assessments_page2) == 2
        
        assessments_page3 = repository.get_all(skip=4, limit=2)
        assert len(assessments_page3) == 1
    
    def test_update_assessment(self, platform_db: Session, create_test_client):
        """Test updating an existing assessment."""
        repository = PlatformAssessmentRepository(platform_db)
        client = create_test_client(name="Test Client")
        
        # Create an assessment
        created_assessment = repository.create({
            "client_id": client.id,
            "assessment_snapshot": {"client_context": {"age": 45}},
            "assessment_status": "draft"
        })
        assessment_id = created_assessment.id
        
        # Update assessment
        update_data = {
            "assessment_status": "finalized",
            "assessment_snapshot": {"client_context": {"age": 46}}
        }
        
        updated_assessment = repository.update(assessment_id, update_data)
        
        assert updated_assessment is not None
        assert updated_assessment.id == assessment_id
        assert updated_assessment.assessment_status == "finalized"
        assert updated_assessment.assessment_snapshot == {"client_context": {"age": 46}}
    
    def test_update_assessment_partial(self, platform_db: Session, create_test_client):
        """Test partial update (only some fields)."""
        repository = PlatformAssessmentRepository(platform_db)
        client = create_test_client(name="Test Client")
        
        # Create an assessment
        created_assessment = repository.create({
            "client_id": client.id,
            "assessment_snapshot": {"client_context": {"age": 45}},
            "assessment_status": "draft"
        })
        assessment_id = created_assessment.id
        
        # Update only status
        update_data = {"assessment_status": "finalized"}
        updated_assessment = repository.update(assessment_id, update_data)
        
        assert updated_assessment is not None
        assert updated_assessment.assessment_status == "finalized"
        assert updated_assessment.assessment_snapshot == {"client_context": {"age": 45}}  # Unchanged
    
    def test_update_assessment_not_found(self, platform_db: Session):
        """Test updating a non-existent assessment."""
        repository = PlatformAssessmentRepository(platform_db)
        
        non_existent_id = uuid4()
        update_data = {"assessment_status": "finalized"}
        
        result = repository.update(non_existent_id, update_data)
        
        assert result is None
    
    def test_delete_assessment(self, platform_db: Session, create_test_client):
        """Test deleting an assessment."""
        repository = PlatformAssessmentRepository(platform_db)
        client = create_test_client(name="Test Client")
        
        # Create an assessment
        created_assessment = repository.create({
            "client_id": client.id,
            "assessment_snapshot": {"client_context": {"age": 45}},
            "assessment_status": "draft"
        })
        assessment_id = created_assessment.id
        
        # Verify assessment exists
        assessment = repository.get_by_id(assessment_id)
        assert assessment is not None
        
        # Delete assessment
        deleted = repository.delete(assessment_id)
        
        assert deleted is True
        
        # Verify assessment is deleted
        assessment_after = repository.get_by_id(assessment_id)
        assert assessment_after is None
    
    def test_delete_assessment_not_found(self, platform_db: Session):
        """Test deleting a non-existent assessment."""
        repository = PlatformAssessmentRepository(platform_db)
        
        non_existent_id = uuid4()
        deleted = repository.delete(non_existent_id)
        
        assert deleted is False
    
    def test_create_assessment_with_complex_snapshot(self, platform_db: Session, create_test_client):
        """Test creating assessment with complex JSONB snapshot."""
        repository = PlatformAssessmentRepository(platform_db)
        client = create_test_client(name="Test Client")
        
        complex_snapshot = {
            "client_context": {
                "age": 45,
                "gender": "Male",
                "height_cm": 170,
                "weight_kg": 75,
                "bmi": 25.95
            },
            "clinical_data": {
                "labs": {"HbA1c": 7.5, "FBS": 140},
                "vitals": {"bp_systolic": 130, "bp_diastolic": 85}
            },
            "lifestyle_data": {
                "sleep": {"hours": 6},
                "stress": {"level": "high"},
                "activity": {"level": "sedentary"}
            }
        }
        
        assessment = repository.create({
            "client_id": client.id,
            "assessment_snapshot": complex_snapshot,
            "assessment_status": "draft"
        })
        
        assert assessment.assessment_snapshot == complex_snapshot

