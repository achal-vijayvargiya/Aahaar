"""
Platform module pytest configuration and fixtures.

This conftest provides test infrastructure specifically for platform module tests.
Platform models use PostgreSQL UUID types, so tests should use PostgreSQL when possible.

IMPORTANT: This conftest creates an isolated FastAPI app with ONLY platform routers.
It does NOT import any legacy code to ensure complete isolation.

Usage:
    - Set TEST_DATABASE_URL environment variable for PostgreSQL testing (recommended)
    - If not set, falls back to SQLite with UUID workaround (limited compatibility)
"""
import os
import pytest
from typing import Generator
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, delete
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Import only platform and core dependencies (NO legacy code)
from app.database import Base, get_db
from app.config import settings

# Import all platform models to ensure they're registered with Base.metadata
from app.platform.data.models import (
    PlatformClient,
    PlatformIntake,
    PlatformAssessment,
    PlatformDiagnosis,
    PlatformMNTConstraint,
    PlatformNutritionTarget,
    PlatformAyurvedaProfile,
    PlatformDietPlan,
    PlatformMonitoringRecord,
    PlatformDecisionLog,
    KBMedicalCondition,
    KBNutritionDiagnosis,
    KBMNTRule,
    KBAyurvedaProfile,
    KBFood,
)

# Import ONLY platform routers (NO legacy routers)
from app.platform.api.clients import router as platform_clients_router
from app.platform.api.assessments import router as platform_assessments_router
from app.platform.api.plans import router as platform_plans_router
from app.platform.api.admin import router as platform_admin_router
from app.platform.api.monitoring import monitoring as platform_monitoring_router

# Create isolated FastAPI app with ONLY platform routers
# This ensures complete isolation from legacy code
platform_test_app = FastAPI(
    title="Platform Test API",
    version="1.0.0",
    description="Isolated test API for platform module (no legacy dependencies)",
)

# Register ONLY platform routers
platform_test_app.include_router(
    platform_clients_router,
    prefix=f"{settings.API_V1_PREFIX}/platform",
    tags=["Platform - Clients"]
)
platform_test_app.include_router(
    platform_assessments_router,
    prefix=f"{settings.API_V1_PREFIX}/platform",
    tags=["Platform - Assessments"]
)
platform_test_app.include_router(
    platform_plans_router,
    prefix=f"{settings.API_V1_PREFIX}/platform",
    tags=["Platform - Plans"]
)
platform_test_app.include_router(
    platform_admin_router,
    prefix=f"{settings.API_V1_PREFIX}/platform",
    tags=["Platform - Admin"]
)
platform_test_app.include_router(
    platform_monitoring_router.router,
    prefix=f"{settings.API_V1_PREFIX}/platform",
    tags=["Platform - Monitoring"]
)

# Get test database URL from environment or use main database
# Platform tests use the same database as the main app (drassistent)
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    None  # Will default to main database if not set
)

if TEST_DATABASE_URL is None:
    # Use the main database for testing (same as production/development)
    TEST_DATABASE_URL = settings.DATABASE_URL

# Determine if we're using PostgreSQL
USE_POSTGRES = TEST_DATABASE_URL and TEST_DATABASE_URL.startswith("postgresql")

if not USE_POSTGRES:
    import warnings
    warnings.warn(
        "Platform tests require PostgreSQL for UUID support. "
        "Set TEST_DATABASE_URL environment variable to a PostgreSQL database URL. "
        "Example: TEST_DATABASE_URL=postgresql://user:pass@localhost:5432/drassistent",
        UserWarning
    )

if USE_POSTGRES:
    # PostgreSQL - full UUID support (recommended)
    engine = create_engine(
        TEST_DATABASE_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        echo=False,  # Set to True for SQL debugging
    )
else:
    # Fallback: Use in-memory SQLite (WARNING: UUID types may not work correctly)
    # This is only for basic structure testing, not full functionality
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

# Create test session factory
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def platform_db() -> Generator[Session, None, None]:
    """
    Create a database session for platform tests.
    
    Creates all platform tables, provides a session, and cleans up after the test.
    Uses transaction rollback for fast cleanup.
    
    Yields:
        Session: Database session for platform tests
    """
    # Create all platform tables
    Base.metadata.create_all(bind=engine)
    
    # Start a transaction
    connection = engine.connect()
    transaction = connection.begin()
    
    # Create session bound to this connection
    session = TestingSessionLocal(bind=connection)
    
    try:
        yield session
    finally:
        # Rollback transaction to undo all changes
        transaction.rollback()
        session.close()
        connection.close()
        
        # Drop all tables after test (optional - can be done at session end)
        # Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def clean_platform_db(platform_db: Session) -> Generator[Session, None, None]:
    """
    Ensure clean database state for each test.
    
    This fixture wraps platform_db and ensures all platform tables are empty
    at the start of each test. Useful for tests that need guaranteed clean state.
    
    Args:
        platform_db: Database session fixture
        
    Yields:
        Session: Clean database session
    """
    # Delete all data from platform tables (in reverse dependency order)
    # Using SQLAlchemy 2.0 style
    platform_db.execute(delete(PlatformMonitoringRecord))
    platform_db.execute(delete(PlatformDietPlan))
    platform_db.execute(delete(PlatformNutritionTarget))
    platform_db.execute(delete(PlatformMNTConstraint))
    platform_db.execute(delete(PlatformDiagnosis))
    platform_db.execute(delete(PlatformAyurvedaProfile))
    platform_db.execute(delete(PlatformAssessment))
    platform_db.execute(delete(PlatformIntake))
    platform_db.execute(delete(PlatformClient))
    platform_db.execute(delete(PlatformDecisionLog))
    
    # Knowledge base tables (usually read-only, but clean for tests)
    platform_db.execute(delete(KBFood))
    platform_db.execute(delete(KBAyurvedaProfile))
    platform_db.execute(delete(KBMNTRule))
    platform_db.execute(delete(KBNutritionDiagnosis))
    platform_db.execute(delete(KBMedicalCondition))
    
    platform_db.commit()
    
    yield platform_db


@pytest.fixture(scope="function")
def platform_client(platform_db: Session) -> Generator[TestClient, None, None]:
    """
    Create a FastAPI TestClient configured for platform endpoints.
    
    Uses isolated platform_test_app (NO legacy code).
    Overrides the get_db dependency to use the test database session.
    All platform endpoints will use this test database.
    
    Args:
        platform_db: Database session fixture
        
    Yields:
        TestClient: FastAPI test client for platform endpoints
    """
    def override_get_db():
        """Override get_db dependency to use test database."""
        try:
            yield platform_db
        finally:
            pass
    
    # Override the dependency on the isolated platform app
    platform_test_app.dependency_overrides[get_db] = override_get_db
    
    # Create test client using isolated platform app
    with TestClient(platform_test_app) as test_client:
        yield test_client
    
    # Clean up
    platform_test_app.dependency_overrides.clear()


# ============================================================================
# TEST DATA FACTORIES
# ============================================================================

@pytest.fixture
def sample_client_data():
    """Sample client data for testing."""
    return {
        "name": "Test Client",
        "age": 30,
        "gender": "Male",
        "height_cm": 175.0,
        "weight_kg": 75.0,
        "location": "Test City",
        "external_client_id": "EXT-001",
    }


@pytest.fixture
def minimal_client_data():
    """Minimal client data (only required fields)."""
    return {
        "name": "Minimal Client",
    }


@pytest.fixture
def create_test_client(platform_db: Session):
    """
    Factory fixture to create test clients.
    
    Usage:
        client = create_test_client(name="Test", age=30)
    
    Args:
        platform_db: Database session
        
    Returns:
        function: Factory function to create test clients
    """
    def _create_client(**kwargs):
        """Create a test client with given attributes."""
        from app.platform.data.repositories.platform_client_repository import PlatformClientRepository
        
        repository = PlatformClientRepository(platform_db)
        client_data = {
            "name": "Test Client",
            "age": 30,
            **kwargs
        }
        return repository.create(client_data)
    
    return _create_client

