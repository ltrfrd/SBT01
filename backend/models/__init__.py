# ===========================================================
# backend/models/__init__.py — BST Models Index
# -----------------------------------------------------------
# Re-exports all models so Alembic can auto-detect them
# ===========================================================

# Import all models here — Alembic uses target_metadata = Base.metadata
# This ensures every model is registered with SQLAlchemy Base

from .driver import Driver
from .school import School
from .student import Student
from .route import Route
from .stop import Stop, StopType
from .run import Run
from .payroll import Payroll
from .associations import route_schools  # Many-to-many table

# Optional: Define __all__ for cleaner imports elsewhere
__all__ = [
    "Driver",
    "School",
    "Student",
    "Route",
    "Stop",
    "StopType",
    "Run",
    "Payroll",
    "route_schools",
]
