# ===========================================================
# database.py
# -----------------------------------------------------------
# Database configuration for BST
# Creates SQLAlchemy engine, session factory, and Base class.
# ===========================================================

from sqlalchemy import create_engine              # Core SQLAlchemy function for DB engine
from sqlalchemy.ext.declarative import declarative_base  # Base class for ORM models
from sqlalchemy.orm import sessionmaker           # Factory for database sessions
from dotenv import load_dotenv                    # Loads .env file variables
import os                                         # Access environment variables

# -----------------------------------------------------------
# Load environment variables from .env
# -----------------------------------------------------------
load_dotenv()  # Reads .env and adds keys to os.environ

# -----------------------------------------------------------
# Get database URL from environment or default to SQLite
# -----------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sbt.db")

# -----------------------------------------------------------
# Create database engine
# connect_args={"check_same_thread": False} is required for SQLite
# (other databases like PostgreSQL don’t need this)
# -----------------------------------------------------------
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

# -----------------------------------------------------------
# Create a configured session factory
# Each request gets its own database session
# -----------------------------------------------------------
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# -----------------------------------------------------------
# Base class for all ORM models
# Each model will inherit from this
# -----------------------------------------------------------
Base = declarative_base()

# -----------------------------------------------------------
# Dependency for FastAPI routes
# Used with Depends(get_db) to provide a session per request
# -----------------------------------------------------------
def get_db():
    db = SessionLocal()       # Create a new DB session
    try:
        yield db              # Provide session to route logic
    finally:
        db.close()            # Close session after use
