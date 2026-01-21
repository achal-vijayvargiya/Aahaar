"""
Tests for Platform Clients API endpoints.

Integration tests for the platform clients API at /api/v1/platform/clients.
"""
import pytest
from uuid import UUID, uuid4
from fastapi.testclient import TestClient

from app.platform.data.repositories.platform_client_repository import PlatformClientRepository


class TestCreateClient:
    """Test suite for POST /api/v1/platform/clients endpoint."""
    
    def test_create_client_success(self, platform_client: TestClient, sample_client_data: dict):
        """Test successful client creation with all fields."""
        response = platform_client.post(
            "/api/v1/platform/clients",
            json=sample_client_data
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert "id" in data
        assert UUID(data["id"])  # Verify it's a valid UUID
        assert data["name"] == "Test Client"
        assert data["age"] == 30
        assert data["gender"] == "Male"
        assert data["height_cm"] == 175.0
        assert data["weight_kg"] == 75.0
        assert data["location"] == "Test City"
        assert data["external_client_id"] == "EXT-001"
        assert "created_at" in data
        assert "updated_at" in data
    
    def test_create_client_minimal(self, platform_client: TestClient, minimal_client_data: dict):
        """Test creating client with only required fields (name)."""
        response = platform_client.post(
            "/api/v1/platform/clients",
            json=minimal_client_data
        )
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["name"] == "Minimal Client"
        assert data["age"] is None
        assert data["gender"] is None
        assert data["height_cm"] is None
        assert data["weight_kg"] is None
        assert data["location"] is None
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
    
    def test_create_client_missing_required_field(self, platform_client: TestClient):
        """Test creating client without required field (name)."""
        response = platform_client.post(
            "/api/v1/platform/clients",
            json={"age": 30}  # Missing name
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_create_client_empty_body(self, platform_client: TestClient):
        """Test creating client with empty request body."""
        response = platform_client.post(
            "/api/v1/platform/clients",
            json={}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_create_client_invalid_data_types(self, platform_client: TestClient):
        """Test creating client with invalid data types."""
        # Invalid age (string instead of int)
        response = platform_client.post(
            "/api/v1/platform/clients",
            json={
                "name": "Test",
                "age": "not-a-number"
            }
        )
        
        assert response.status_code == 422
    
    def test_create_client_negative_age(self, platform_client: TestClient):
        """Test creating client with negative age (should be allowed or validated)."""
        response = platform_client.post(
            "/api/v1/platform/clients",
            json={
                "name": "Test",
                "age": -5
            }
        )
        
        # Age validation depends on model - might succeed or fail
        # This test documents the current behavior
        assert response.status_code in [201, 422]
    
    def test_create_client_very_long_name(self, platform_client: TestClient):
        """Test creating client with very long name."""
        long_name = "A" * 1000
        response = platform_client.post(
            "/api/v1/platform/clients",
            json={"name": long_name}
        )
        
        # Should either succeed or fail with appropriate error
        assert response.status_code in [201, 422]


class TestGetClients:
    """Test suite for GET /api/v1/platform/clients endpoint."""
    
    def test_get_clients_empty(self, platform_client: TestClient):
        """Test getting clients from empty database."""
        response = platform_client.get("/api/v1/platform/clients")
        
        assert response.status_code == 200
        data = response.json()
        assert data == []
        assert len(data) == 0
    
    def test_get_clients_with_data(self, platform_client: TestClient, create_test_client):
        """Test getting clients when database has data."""
        # Create multiple clients
        create_test_client(name="Client 1")
        create_test_client(name="Client 2")
        create_test_client(name="Client 3")
        
        response = platform_client.get("/api/v1/platform/clients")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert all("id" in client for client in data)
        assert all("name" in client for client in data)
    
    def test_get_clients_pagination_skip(self, platform_client: TestClient, create_test_client):
        """Test pagination with skip parameter."""
        # Create 5 clients
        for i in range(5):
            create_test_client(name=f"Client {i}")
        
        # Get first page
        response = platform_client.get("/api/v1/platform/clients?skip=0&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        
        # Get second page
        response = platform_client.get("/api/v1/platform/clients?skip=2&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        
        # Get third page
        response = platform_client.get("/api/v1/platform/clients?skip=4&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
    
    def test_get_clients_pagination_limit(self, platform_client: TestClient, create_test_client):
        """Test pagination with limit parameter."""
        # Create 10 clients
        for i in range(10):
            create_test_client(name=f"Client {i}")
        
        # Get with limit
        response = platform_client.get("/api/v1/platform/clients?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5
    
    def test_get_clients_default_pagination(self, platform_client: TestClient, create_test_client):
        """Test default pagination values."""
        # Create more than default limit (100)
        for i in range(150):
            create_test_client(name=f"Client {i}")
        
        response = platform_client.get("/api/v1/platform/clients")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 100  # Default limit
    
    def test_get_clients_invalid_skip(self, platform_client: TestClient):
        """Test with invalid skip parameter."""
        response = platform_client.get("/api/v1/platform/clients?skip=-1")
        assert response.status_code == 422  # Validation error
    
    def test_get_clients_invalid_limit(self, platform_client: TestClient):
        """Test with invalid limit parameter."""
        response = platform_client.get("/api/v1/platform/clients?limit=0")
        assert response.status_code == 422  # Validation error (limit must be >= 1)


class TestGetClientById:
    """Test suite for GET /api/v1/platform/clients/{id} endpoint."""
    
    def test_get_client_by_id_success(self, platform_client: TestClient, create_test_client):
        """Test successfully retrieving a client by ID."""
        # Create a test client
        created = create_test_client(name="Test Client", age=30)
        client_id = str(created.id)
        
        response = platform_client.get(f"/api/v1/platform/clients/{client_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == client_id
        assert data["name"] == "Test Client"
        assert data["age"] == 30
        assert "created_at" in data
        assert "updated_at" in data
    
    def test_get_client_by_id_verify_all_fields(self, platform_client: TestClient, sample_client_data: dict):
        """Test that all fields are returned correctly."""
        # Create client with all fields
        create_response = platform_client.post(
            "/api/v1/platform/clients",
            json=sample_client_data
        )
        client_id = create_response.json()["id"]
        
        # Retrieve client
        response = platform_client.get(f"/api/v1/platform/clients/{client_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all fields
        assert data["name"] == "Test Client"
        assert data["age"] == 30
        assert data["gender"] == "Male"
        assert data["height_cm"] == 175.0
        assert data["weight_kg"] == 75.0
        assert data["location"] == "Test City"
        assert data["external_client_id"] == "EXT-001"
    
    def test_get_client_not_found(self, platform_client: TestClient):
        """Test retrieving a non-existent client."""
        non_existent_id = str(uuid4())
        
        response = platform_client.get(f"/api/v1/platform/clients/{non_existent_id}")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_get_client_invalid_uuid_format(self, platform_client: TestClient):
        """Test with invalid UUID format."""
        invalid_id = "not-a-uuid"
        
        response = platform_client.get(f"/api/v1/platform/clients/{invalid_id}")
        
        # FastAPI should return 422 for invalid UUID format
        assert response.status_code == 422


class TestUpdateClient:
    """Test suite for PUT /api/v1/platform/clients/{id} endpoint."""
    
    def test_update_client_success(self, platform_client: TestClient, create_test_client):
        """Test successfully updating a client."""
        # Create a test client
        created = create_test_client(name="Original Name", age=25)
        client_id = str(created.id)
        
        # Update client
        update_data = {
            "name": "Updated Name",
            "age": 30,
            "weight_kg": 80.0,
        }
        
        response = platform_client.put(
            f"/api/v1/platform/clients/{client_id}",
            json=update_data
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == client_id
        assert data["name"] == "Updated Name"
        assert data["age"] == 30
        assert data["weight_kg"] == 80.0
    
    def test_update_client_partial(self, platform_client: TestClient, create_test_client):
        """Test partial update (only some fields)."""
        # Create a test client
        created = create_test_client(name="Original", age=25, gender="Male")
        client_id = str(created.id)
        
        # Update only age
        update_data = {"age": 30}
        
        response = platform_client.put(
            f"/api/v1/platform/clients/{client_id}",
            json=update_data
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["name"] == "Original"  # Unchanged
        assert data["age"] == 30  # Updated
        assert data["gender"] == "Male"  # Unchanged
    
    def test_update_client_all_fields(self, platform_client: TestClient, create_test_client):
        """Test updating all fields."""
        # Create a test client
        created = create_test_client(name="Original")
        client_id = str(created.id)
        
        # Update all fields
        update_data = {
            "name": "Updated Name",
            "age": 35,
            "gender": "Female",
            "height_cm": 165.0,
            "weight_kg": 60.0,
            "location": "New City",
        }
        
        response = platform_client.put(
            f"/api/v1/platform/clients/{client_id}",
            json=update_data
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["name"] == "Updated Name"
        assert data["age"] == 35
        assert data["gender"] == "Female"
        assert data["height_cm"] == 165.0
        assert data["weight_kg"] == 60.0
        assert data["location"] == "New City"
    
    def test_update_client_not_found(self, platform_client: TestClient):
        """Test updating a non-existent client."""
        non_existent_id = str(uuid4())
        update_data = {"name": "Updated Name"}
        
        response = platform_client.put(
            f"/api/v1/platform/clients/{non_existent_id}",
            json=update_data
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_update_client_empty_body(self, platform_client: TestClient, create_test_client):
        """Test update with empty request body."""
        created = create_test_client(name="Test")
        client_id = str(created.id)
        
        response = platform_client.put(
            f"/api/v1/platform/clients/{client_id}",
            json={}
        )
        
        # Should return 400 - no fields to update
        assert response.status_code == 400
        data = response.json()
        assert "no fields" in data["detail"].lower() or "provided" in data["detail"].lower()
    
    def test_update_client_invalid_uuid(self, platform_client: TestClient):
        """Test update with invalid UUID format."""
        invalid_id = "not-a-uuid"
        update_data = {"name": "Updated"}
        
        response = platform_client.put(
            f"/api/v1/platform/clients/{invalid_id}",
            json=update_data
        )
        
        assert response.status_code == 422  # Validation error


class TestDeleteClient:
    """Test suite for DELETE /api/v1/platform/clients/{id} endpoint."""
    
    def test_delete_client_success(self, platform_client: TestClient, create_test_client):
        """Test successfully deleting a client."""
        # Create a test client
        created = create_test_client(name="To Be Deleted")
        client_id = str(created.id)
        
        # Verify client exists
        get_response = platform_client.get(f"/api/v1/platform/clients/{client_id}")
        assert get_response.status_code == 200
        
        # Delete client
        response = platform_client.delete(f"/api/v1/platform/clients/{client_id}")
        
        assert response.status_code == 204
        assert response.content == b""  # No content
        
        # Verify client is deleted
        get_response_after = platform_client.get(f"/api/v1/platform/clients/{client_id}")
        assert get_response_after.status_code == 404
    
    def test_delete_client_not_found(self, platform_client: TestClient):
        """Test deleting a non-existent client."""
        non_existent_id = str(uuid4())
        
        response = platform_client.delete(f"/api/v1/platform/clients/{non_existent_id}")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
    
    def test_delete_client_invalid_uuid(self, platform_client: TestClient):
        """Test delete with invalid UUID format."""
        invalid_id = "not-a-uuid"
        
        response = platform_client.delete(f"/api/v1/platform/clients/{invalid_id}")
        
        assert response.status_code == 422  # Validation error


class TestClientEdgeCases:
    """Test suite for edge cases and error handling."""
    
    def test_create_client_with_none_values(self, platform_client: TestClient):
        """Test creating client with explicit None values."""
        client_data = {
            "name": "Test Client",
            "age": None,
            "gender": None,
        }
        
        response = platform_client.post(
            "/api/v1/platform/clients",
            json=client_data
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Client"
        assert data["age"] is None
        assert data["gender"] is None
    
    def test_update_client_set_to_none(self, platform_client: TestClient, create_test_client):
        """Test updating client field to None."""
        created = create_test_client(name="Test", age=30)
        client_id = str(created.id)
        
        # Update age to None
        update_data = {"age": None}
        
        response = platform_client.put(
            f"/api/v1/platform/clients/{client_id}",
            json=update_data
        )
        
        # Should succeed - None is valid for optional fields
        assert response.status_code == 200
        data = response.json()
        assert data["age"] is None
    
    def test_get_clients_max_limit(self, platform_client: TestClient, create_test_client):
        """Test getting clients with maximum limit."""
        # Create clients
        for i in range(50):
            create_test_client(name=f"Client {i}")
        
        # Request with max limit (1000)
        response = platform_client.get("/api/v1/platform/clients?limit=1000")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 50  # Only 50 exist
    
    def test_get_clients_large_skip(self, platform_client: TestClient, create_test_client):
        """Test pagination with skip larger than total records."""
        # Create 5 clients
        for i in range(5):
            create_test_client(name=f"Client {i}")
        
        # Skip more than total
        response = platform_client.get("/api/v1/platform/clients?skip=100")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0  # Empty result

