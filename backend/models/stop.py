# ===========================================================
# backend/models/stop.py — BST Stop Model
# -----------------------------------------------------------
# Defines the Stop table using numeric order instead of names.
# Each stop belongs to a route and can be pickup or dropoff.
# ===========================================================
from sqlalchemy import Column, Integer, ForeignKey, Enum
from sqlalchemy.orm import relationship
from database import Base  # Root-level
import enum

# -----------------------------------------------------------
# Stop type enum: pickup or dropoff
# -----------------------------------------------------------
class StopType(str, enum.Enum):
    PICKUP = "pickup"
    DROPOFF = "dropoff"

# -----------------------------------------------------------
# Stop model
# -----------------------------------------------------------
class Stop(Base):
    __tablename__ = "stops"

    id = Column(Integer, primary_key=True, index=True)  # Unique stop ID
    sequence = Column(Integer, nullable=False)          # Numeric order (1, 2, 3...)
    type = Column(Enum(StopType), nullable=False)       # Stop type (pickup/dropoff)
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=False)  # Linked route

    # -------------------------------------------------------
    # Relationships
    # -------------------------------------------------------
    route = relationship("Route", back_populates="stops")      # Each stop belongs to one route
    students = relationship("Student", back_populates="stop")  # Students linked to this stop