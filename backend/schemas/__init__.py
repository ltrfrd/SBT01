# ===========================================================
# backend/schemas/__init__.py — SBT Schemas Index
# -----------------------------------------------------------
# Centralized import hub for all Pydantic schemas.
# Routers and modules can import from here instead of each file.
# ===========================================================

# -----------------------------------------------------------
# Import each schema module explicitly
# -----------------------------------------------------------
# backend/schemas/__init__.py

from .driver import DriverCreate, DriverOut
from .school import SchoolCreate, SchoolOut
from .route import RouteCreate, RouteOut
from .stop import StopCreate  # Import schema used for creating stops
from .stop import StopOut  # Import schema used for returning stops
from .student import StudentCreate, StudentOut
from .run import  RunOut  # Run request/response
from .payroll import PayrollCreate, PayrollOut  # Payroll (view + charter)

# -----------------------------------------------------------
# Control what is exported when using 'from backend.schemas import *'
# -----------------------------------------------------------
__all__ = [
    "DriverCreate",
    "DriverOut",
    "SchoolCreate",
    "SchoolOut",
    "StudentCreate",
    "StudentOut",
    "RouteCreate",
    "RouteOut",
    "StopCreate",
    "StopOut",
    "RunCreate",
    "RunOut",
    "PayrollCreate",
    "PayrollOut",
]
