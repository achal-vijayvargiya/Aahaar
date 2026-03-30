"""Pytest configuration for tests that target the full ASGI app (app.main).

Platform/NCP tests use ``tests/platform/conftest.py`` and do not import this module
for fixtures. Auth tests live under ``tests/platform/api/test_auth.py``.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Lazy import so a broken or partially-upgraded local env does not break collection
# of the entire test tree (platform tests stay usable).
try:
    from app.main import app
    from app.database import Base, get_db
    LEGACY_APP_AVAILABLE = True
except Exception:
    LEGACY_APP_AVAILABLE = False
    app = None
    Base = None
    get_db = None

if LEGACY_APP_AVAILABLE:
    # SQLite for tests that need a test DB session (platform models use
    # postgresql.UUID and cannot be created on SQLite — use PostgreSQL or
    # platform conftest for those).
    SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    @pytest.fixture
    def app_client():
        """TestClient for ``app.main`` without replacing ``get_db`` (smoke tests)."""
        with TestClient(app) as test_client:
            yield test_client

    @pytest.fixture
    def db():
        """SQLite session + schema for tests that override ``get_db``."""
        if not LEGACY_APP_AVAILABLE:
            pytest.skip("app.main not importable; use platform tests under tests/platform/")
        Base.metadata.create_all(bind=engine)
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
            Base.metadata.drop_all(bind=engine)


    @pytest.fixture
    def client(db):
        """TestClient for ``app.main`` with DB override."""
        if not LEGACY_APP_AVAILABLE:
            pytest.skip("app.main not importable; use platform tests under tests/platform/")
        def override_get_db():
            try:
                yield db
            finally:
                pass
        
        app.dependency_overrides[get_db] = override_get_db
        with TestClient(app) as test_client:
            yield test_client
        app.dependency_overrides.clear()

