"""
Tests for Platform Intake Repository.

Unit tests for the data layer - testing repository methods in isolation.
"""
import pytest
from uuid import UUID, uuid4
from sqlalchemy.orm import Session

from app.platform.data.repositories.platform_intake_repository import PlatformIntakeRepository
from app.platform.data.models.platform_intake import PlatformIntake
from app.platform.data.repositories.platform_client_repository import PlatformClientRepository


class TestPlatformIntakeRepository:
    """Test suite for PlatformIntakeRepository."""
    
    def test_create_intake(self, platform_db: Session, create_test_client):
        """Test creating a new intake."""
        repository = PlatformIntakeRepository(platform_db)
        client = create_test_client(name="Test Client")
        
        intake_data = {
            "client_id": client.id,
            "raw_input": {
                "labs": {"HbA1c": 7.5},
                "vitals": {"weight_kg": 75}
            },
            "source": "manual"
        }
        
        intake = repository.create(intake_data)
        
        assert intake is not None
        assert intake.id is not None
        assert isinstance(intake.id, UUID)
        assert intake.client_id == client.id
        assert intake.source == "manual"
        assert intake.raw_input == {"labs": {"HbA1c": 7.5}, "vitals": {"weight_kg": 75}}
        assert intake.normalized_input is None
        assert intake.created_at is not None
    
    def test_create_intake_minimal(self, platform_db: Session, create_test_client):
        """Test creating an intake with only required fields."""
        repository = PlatformIntakeRepository(platform_db)
        client = create_test_client(name="Test Client")
        
        intake_data = {
            "client_id": client.id
        }
        
        intake = repository.create(intake_data)
        
        assert intake is not None
        assert intake.id is not None
        assert intake.client_id == client.id
        assert intake.raw_input is None
        assert intake.source is None
    
    def test_get_by_id(self, platform_db: Session, create_test_client):
        """Test retrieving an intake by ID."""
        repository = PlatformIntakeRepository(platform_db)
        client = create_test_client(name="Test Client")
        
        # Create an intake
        created_intake = repository.create({
            "client_id": client.id,
            "raw_input": {"labs": {"HbA1c": 7.5}},
            "source": "manual"
        })
        intake_id = created_intake.id
        
        # Retrieve by ID
        intake = repository.get_by_id(intake_id)
        
        assert intake is not None
        assert intake.id == intake_id
        assert intake.client_id == client.id
        assert intake.source == "manual"
    
    def test_get_by_id_not_found(self, platform_db: Session):
        """Test retrieving a non-existent intake by ID."""
        repository = PlatformIntakeRepository(platform_db)
        
        non_existent_id = uuid4()
        intake = repository.get_by_id(non_existent_id)
        
        assert intake is None
    
    def test_get_by_client_id(self, platform_db: Session, create_test_client):
        """Test retrieving intakes by client ID."""
        repository = PlatformIntakeRepository(platform_db)
        client = create_test_client(name="Test Client")
        
        # Create multiple intakes for the client
        for i in range(3):
            repository.create({
                "client_id": client.id,
                "raw_input": {"labs": {"HbA1c": 7.5 + i}},
                "source": "manual"
            })
        
        # Retrieve all intakes for client
        intakes = repository.get_by_client_id(client.id)
        
        assert len(intakes) == 3
        assert all(intake.client_id == client.id for intake in intakes)
    
    def test_get_by_client_id_empty(self, platform_db: Session, create_test_client):
        """Test getting intakes for client with no intakes."""
        repository = PlatformIntakeRepository(platform_db)
        client = create_test_client(name="Test Client")
        
        intakes = repository.get_by_client_id(client.id)
        
        assert intakes == []
        assert len(intakes) == 0
    
    def test_get_all_empty(self, platform_db: Session):
        """Test getting all intakes from empty database."""
        repository = PlatformIntakeRepository(platform_db)
        
        intakes = repository.get_all()
        
        assert intakes == []
        assert len(intakes) == 0
    
    def test_get_all_pagination(self, platform_db: Session, create_test_client):
        """Test getting all intakes with pagination."""
        repository = PlatformIntakeRepository(platform_db)
        client = create_test_client(name="Test Client")
        
        # Create multiple intakes
        for i in range(5):
            repository.create({
                "client_id": client.id,
                "raw_input": {"labs": {"HbA1c": 7.5 + i}},
                "source": "manual"
            })
        
        # Test pagination
        intakes_page1 = repository.get_all(skip=0, limit=2)
        assert len(intakes_page1) == 2
        
        intakes_page2 = repository.get_all(skip=2, limit=2)
        assert len(intakes_page2) == 2
        
        intakes_page3 = repository.get_all(skip=4, limit=2)
        assert len(intakes_page3) == 1
    
    def test_update_intake(self, platform_db: Session, create_test_client):
        """Test updating an existing intake."""
        repository = PlatformIntakeRepository(platform_db)
        client = create_test_client(name="Test Client")
        
        # Create an intake
        created_intake = repository.create({
            "client_id": client.id,
            "raw_input": {"labs": {"HbA1c": 7.5}},
            "source": "manual"
        })
        intake_id = created_intake.id
        
        # Update intake
        update_data = {
            "source": "ai_extracted",
            "raw_input": {"labs": {"HbA1c": 8.0}}
        }
        
        updated_intake = repository.update(intake_id, update_data)
        
        assert updated_intake is not None
        assert updated_intake.id == intake_id
        assert updated_intake.source == "ai_extracted"
        assert updated_intake.raw_input == {"labs": {"HbA1c": 8.0}}
    
    def test_update_intake_not_found(self, platform_db: Session):
        """Test updating a non-existent intake."""
        repository = PlatformIntakeRepository(platform_db)
        
        non_existent_id = uuid4()
        update_data = {"source": "manual"}
        
        result = repository.update(non_existent_id, update_data)
        
        assert result is None
    
    def test_delete_intake(self, platform_db: Session, create_test_client):
        """Test deleting an intake."""
        repository = PlatformIntakeRepository(platform_db)
        client = create_test_client(name="Test Client")
        
        # Create an intake
        created_intake = repository.create({
            "client_id": client.id,
            "raw_input": {"labs": {"HbA1c": 7.5}},
            "source": "manual"
        })
        intake_id = created_intake.id
        
        # Verify intake exists
        intake = repository.get_by_id(intake_id)
        assert intake is not None
        
        # Delete intake
        deleted = repository.delete(intake_id)
        
        assert deleted is True
        
        # Verify intake is deleted
        intake_after = repository.get_by_id(intake_id)
        assert intake_after is None
    
    def test_delete_intake_not_found(self, platform_db: Session):
        """Test deleting a non-existent intake."""
        repository = PlatformIntakeRepository(platform_db)
        
        non_existent_id = uuid4()
        deleted = repository.delete(non_existent_id)
        
        assert deleted is False
    
    def test_create_intake_with_all_sources(self, platform_db: Session, create_test_client):
        """Test creating intakes with different source values."""
        repository = PlatformIntakeRepository(platform_db)
        client = create_test_client(name="Test Client")
        
        sources = ["manual", "upload", "ai_extracted"]
        
        for source in sources:
            intake = repository.create({
                "client_id": client.id,
                "source": source
            })
            
            assert intake.source == source
    
    def test_create_intake_with_complex_raw_input(self, platform_db: Session, create_test_client):
        """Test creating intake with complex JSONB raw_input."""
        repository = PlatformIntakeRepository(platform_db)
        client = create_test_client(name="Test Client")
        
        complex_raw_input = {
            "labs": {
                "HbA1c": 7.5,
                "FBS": 140,
                "cholesterol": 220
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
            }
        }
        
        intake = repository.create({
            "client_id": client.id,
            "raw_input": complex_raw_input,
            "source": "manual"
        })
        
        assert intake.raw_input == complex_raw_input

