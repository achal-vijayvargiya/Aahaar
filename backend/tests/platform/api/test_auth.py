"""Platform auth API tests (/api/v1/platform/auth/*)."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.platform.data.repositories.platform_user_repository import (
    PlatformUserRepository,
)
from app.platform.utils.security import get_password_hash


AUTH_LOGIN = "/api/v1/platform/auth/login"
AUTH_ME = "/api/v1/platform/auth/me"


class TestPlatformAuth:
    def test_login_success(self, platform_client: TestClient, platform_db: Session):
        repo = PlatformUserRepository(platform_db)
        repo.create(
            {
                "email": "test@example.com",
                "username": "testuser",
                "hashed_password": get_password_hash("testpass123"),
                "full_name": "Test User",
                "is_active": True,
            }
        )
        response = platform_client.post(
            AUTH_LOGIN,
            data={"username": "testuser", "password": "testpass123"},
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_credentials(self, platform_client: TestClient):
        response = platform_client.post(
            AUTH_LOGIN,
            data={"username": "nonexistent", "password": "wrongpass"},
        )
        assert response.status_code == 401

    def test_get_current_user(self, platform_client: TestClient, platform_db: Session):
        repo = PlatformUserRepository(platform_db)
        repo.create(
            {
                "email": "me@example.com",
                "username": "meuser",
                "hashed_password": get_password_hash("testpass123"),
                "full_name": "Me User",
                "is_active": True,
            }
        )
        login_response = platform_client.post(
            AUTH_LOGIN,
            data={"username": "meuser", "password": "testpass123"},
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        response = platform_client.get(
            AUTH_ME,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "meuser"
        assert data["email"] == "me@example.com"
