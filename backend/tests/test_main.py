"""Tests for main application endpoints."""
import pytest
from fastapi.testclient import TestClient


def test_root_endpoint(app_client):
    """Test root endpoint."""
    response = app_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert data["message"] == "Welcome to DrAssistent API"


def test_health_check(app_client):
    """Test health check endpoint."""
    response = app_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "environment" in data


def test_docs_available(app_client):
    """Test that API documentation is available."""
    response = app_client.get("/docs")
    assert response.status_code == 200
    
    response = app_client.get("/redoc")
    assert response.status_code == 200

