"""
Tests for Platform Client Repository.

Unit tests for the data layer - testing repository methods in isolation.
"""
import pytest
from uuid import UUID, uuid4
from sqlalchemy.orm import Session

from app.platform.data.repositories.platform_client_repository import PlatformClientRepository
from app.platform.data.models.platform_client import PlatformClient


class TestPlatformClientRepository:
    """Test suite for PlatformClientRepository."""
    
    def test_create_client(self, platform_db: Session):
        """Test creating a new client."""
        repository = PlatformClientRepository(platform_db)
        
        client_data = {
            "name": "Test Client",
            "age": 30,
            "gender": "Male",
            "height_cm": 175.0,
            "weight_kg": 75.0,
            "location": "Test City",
        }
        
        client = repository.create(client_data)
        
        assert client is not None
        assert client.id is not None
        assert isinstance(client.id, UUID)
        assert client.name == "Test Client"
        assert client.age == 30
        assert client.gender == "Male"
        assert client.height_cm == 175.0
        assert client.weight_kg == 75.0
        assert client.location == "Test City"
        assert client.created_at is not None
        assert client.updated_at is not None
    
    def test_create_client_minimal(self, platform_db: Session):
        """Test creating a client with only required fields."""
        repository = PlatformClientRepository(platform_db)
        
        client_data = {
            "name": "Minimal Client",
        }
        
        client = repository.create(client_data)
        
        assert client is not None
        assert client.id is not None
        assert client.name == "Minimal Client"
        assert client.age is None
        assert client.gender is None
    
    def test_get_by_id(self, platform_db: Session, create_test_client):
        """Test retrieving a client by ID."""
        repository = PlatformClientRepository(platform_db)
        
        # Create a test client
        created_client = create_test_client(name="Test Client")
        client_id = created_client.id
        
        # Retrieve by ID
        client = repository.get_by_id(client_id)
        
        assert client is not None
        assert client.id == client_id
        assert client.name == "Test Client"
    
    def test_get_by_id_not_found(self, platform_db: Session):
        """Test retrieving a non-existent client by ID."""
        repository = PlatformClientRepository(platform_db)
        
        # Try to retrieve with a random UUID
        non_existent_id = uuid4()
        client = repository.get_by_id(non_existent_id)
        
        assert client is None
    
    def test_get_by_external_id(self, platform_db: Session, create_test_client):
        """Test retrieving a client by external ID."""
        repository = PlatformClientRepository(platform_db)
        
        # Create a test client with external ID
        created_client = create_test_client(
            name="External Client",
            external_client_id="EXT-001"
        )
        
        # Retrieve by external ID
        client = repository.get_by_external_id("EXT-001")
        
        assert client is not None
        assert client.external_client_id == "EXT-001"
        assert client.name == "External Client"
    
    def test_get_by_external_id_not_found(self, platform_db: Session):
        """Test retrieving a client with non-existent external ID."""
        repository = PlatformClientRepository(platform_db)
        
        client = repository.get_by_external_id("NON-EXISTENT")
        
        assert client is None
    
    def test_get_all_empty(self, platform_db: Session):
        """Test getting all clients from empty database."""
        repository = PlatformClientRepository(platform_db)
        
        clients = repository.get_all()
        
        assert clients == []
        assert len(clients) == 0
    
    def test_get_all_pagination(self, platform_db: Session, create_test_client):
        """Test getting all clients with pagination."""
        repository = PlatformClientRepository(platform_db)
        
        # Create multiple clients
        for i in range(5):
            create_test_client(name=f"Client {i}")
        
        # Test pagination
        clients_page1 = repository.get_all(skip=0, limit=2)
        assert len(clients_page1) == 2
        
        clients_page2 = repository.get_all(skip=2, limit=2)
        assert len(clients_page2) == 2
        
        clients_page3 = repository.get_all(skip=4, limit=2)
        assert len(clients_page3) == 1
        
        # Verify all clients are different
        all_ids = {c.id for c in clients_page1 + clients_page2 + clients_page3}
        assert len(all_ids) == 5
    
    def test_get_all_with_limit(self, platform_db: Session, create_test_client):
        """Test getting all clients with limit."""
        repository = PlatformClientRepository(platform_db)
        
        # Create 10 clients
        for i in range(10):
            create_test_client(name=f"Client {i}")
        
        # Get with limit
        clients = repository.get_all(skip=0, limit=5)
        assert len(clients) == 5
        
        # Get all
        all_clients = repository.get_all(skip=0, limit=100)
        assert len(all_clients) == 10
    
    def test_update_client(self, platform_db: Session, create_test_client):
        """Test updating an existing client."""
        repository = PlatformClientRepository(platform_db)
        
        # Create a test client
        created_client = create_test_client(
            name="Original Name",
            age=25,
            height_cm=170.0
        )
        client_id = created_client.id
        
        # Update client
        update_data = {
            "name": "Updated Name",
            "age": 26,
            "weight_kg": 80.0,
        }
        
        updated_client = repository.update(client_id, update_data)
        
        assert updated_client is not None
        assert updated_client.id == client_id
        assert updated_client.name == "Updated Name"
        assert updated_client.age == 26
        assert updated_client.height_cm == 170.0  # Should remain unchanged
        assert updated_client.weight_kg == 80.0  # Should be updated
        assert updated_client.updated_at is not None
    
    def test_update_client_partial(self, platform_db: Session, create_test_client):
        """Test partial update (only some fields)."""
        repository = PlatformClientRepository(platform_db)
        
        # Create a test client
        created_client = create_test_client(
            name="Original Name",
            age=25,
            gender="Male"
        )
        client_id = created_client.id
        
        # Update only age
        update_data = {"age": 30}
        updated_client = repository.update(client_id, update_data)
        
        assert updated_client is not None
        assert updated_client.name == "Original Name"  # Unchanged
        assert updated_client.age == 30  # Updated
        assert updated_client.gender == "Male"  # Unchanged
    
    def test_update_client_not_found(self, platform_db: Session):
        """Test updating a non-existent client."""
        repository = PlatformClientRepository(platform_db)
        
        non_existent_id = uuid4()
        update_data = {"name": "Updated Name"}
        
        result = repository.update(non_existent_id, update_data)
        
        assert result is None
    
    def test_delete_client(self, platform_db: Session, create_test_client):
        """Test deleting a client."""
        repository = PlatformClientRepository(platform_db)
        
        # Create a test client
        created_client = create_test_client(name="To Be Deleted")
        client_id = created_client.id
        
        # Verify client exists
        client = repository.get_by_id(client_id)
        assert client is not None
        
        # Delete client
        deleted = repository.delete(client_id)
        
        assert deleted is True
        
        # Verify client is deleted
        client_after = repository.get_by_id(client_id)
        assert client_after is None
    
    def test_delete_client_not_found(self, platform_db: Session):
        """Test deleting a non-existent client."""
        repository = PlatformClientRepository(platform_db)
        
        non_existent_id = uuid4()
        deleted = repository.delete(non_existent_id)
        
        assert deleted is False
    
    def test_create_client_with_external_id(self, platform_db: Session):
        """Test creating a client with external client ID."""
        repository = PlatformClientRepository(platform_db)
        
        client_data = {
            "name": "External Client",
            "external_client_id": "EXT-12345",
        }
        
        client = repository.create(client_data)
        
        assert client is not None
        assert client.external_client_id == "EXT-12345"
        
        # Verify we can retrieve by external ID
        retrieved = repository.get_by_external_id("EXT-12345")
        assert retrieved is not None
        assert retrieved.id == client.id

