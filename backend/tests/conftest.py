"""Pytest configuration and fixtures for legacy tests."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Lazy import to avoid breaking platform tests
# Platform tests use their own isolated conftest
try:
    from app.main import app
    from app.database import Base, get_db
    LEGACY_APP_AVAILABLE = True
except (ImportError, ModuleNotFoundError) as e:
    # Legacy app not available (e.g., when running platform-only tests)
    # This is OK - platform tests have their own conftest
    LEGACY_APP_AVAILABLE = False
    app = None
    Base = None
    get_db = None

# Only set up legacy fixtures if legacy app is available
if LEGACY_APP_AVAILABLE:
    # Create in-memory SQLite database for testing
    SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


    @pytest.fixture
    def db():
        """Create database tables and provide a database session (legacy tests only)."""
        if not LEGACY_APP_AVAILABLE:
            pytest.skip("Legacy app not available - use platform tests instead")
        Base.metadata.create_all(bind=engine)
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
            Base.metadata.drop_all(bind=engine)


    @pytest.fixture
    def client(db):
        """Create a test client with database override (legacy tests only)."""
        if not LEGACY_APP_AVAILABLE:
            pytest.skip("Legacy app not available - use platform tests instead")
        def override_get_db():
            try:
                yield db
            finally:
                pass
        
        app.dependency_overrides[get_db] = override_get_db
        with TestClient(app) as test_client:
            yield test_client
        app.dependency_overrides.clear()

