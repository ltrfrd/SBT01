# =============================================================================
# tests/conftest.py
# -----------------------------------------------------------------------------
# Shared pytest fixtures:
#   - Ensure repo root is on sys.path so `import backend` works (Windows-safe)
#   - Create isolated SQLite DB per test (tmp_path)
#   - FastAPI TestClient with get_db overridden to use the test DB
# =============================================================================

# =============================================================================
# PATH FIX (MUST BE FIRST)
# -----------------------------------------------------------------------------
# Pytest imports conftest.py before running tests.
# If repo root isn't on sys.path, `import backend` will fail.
# =============================================================================

import os  # Path utilities
import sys  # Python import path control

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))  # Repo root (SBT01)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)  # Add repo root so `backend` is importable


# =============================================================================
# Imports (after PATH FIX)
# =============================================================================

import pytest  # Pytest fixtures
from sqlalchemy import create_engine  # DB engine factory
from sqlalchemy.orm import sessionmaker  # Session factory

from database import Base  # SQLAlchemy Base (root database.py)
from app import app, get_db  # FastAPI app + DB dependency


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture()
def db_engine(tmp_path):
    """Create a temporary SQLite engine for this test (isolated from sbt.db)."""

    test_db_path = tmp_path / "test_sbt.db"  # Unique per-test temp DB file

    engine = create_engine(
        f"sqlite:///{test_db_path}",  # File-based SQLite inside tmp directory
        connect_args={"check_same_thread": False},  # Required for TestClient threads
    )

    Base.metadata.create_all(bind=engine)  # Create tables fresh
    yield engine  # Provide engine to tests
    Base.metadata.drop_all(bind=engine)  # Drop tables after test
    engine.dispose()  # Release file handles (important on Windows)


@pytest.fixture()
def client(db_engine):
    """FastAPI TestClient with get_db overridden to use the temporary test DB."""

    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=db_engine,
    )

    def override_get_db():
        db = TestingSessionLocal()  # New session per request
        try:
            yield db
        finally:
            db.close()

    # Override dependency for this test
    app.dependency_overrides[get_db] = override_get_db

    from fastapi.testclient import TestClient  # Imported here to keep fixture self-contained

    with TestClient(app) as c:
        yield c

    # Remove overrides so they don't leak into other tests
    app.dependency_overrides.clear()