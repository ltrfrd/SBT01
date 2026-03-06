# ===========================================================
# backend/schemas/stop.py — SBT Stop Schemas
# -----------------------------------------------------------
# Pydantic models for Stop creation and output responses.
# Stops are identified primarily by sequence number.
# ===========================================================

from pydantic import BaseModel, ConfigDict            # Base schema tools
from enum import Enum                                 # Enum support
from typing import Optional                           # Optional fields
from datetime import time                             # Time type for planned stop time



# -----------------------------------------------------------
# Stop type enum: pickup or dropoff
# -----------------------------------------------------------
class StopType(str, Enum):
    PICKUP = "pickup"
    DROPOFF = "dropoff"


# -----------------------------------------------------------
# Schema for creating a stop (POST request)
# -----------------------------------------------------------
class StopCreate(BaseModel):                                   # Create schema
    route_id: int                                              # Required route id
    type: str                                                  # Required ("pickup" or "dropoff")
    sequence: Optional[int] = None                             # Optional; backend can auto-set

    name: Optional[str] = None                                 # Optional stop name
    address: Optional[str] = None                              # Optional address

    latitude: Optional[float] = None                           # Optional latitude
    longitude: Optional[float] = None                          # Optional longitude


class StopUpdate(BaseModel):  # Partial update schema for Stop
    sequence: int | None = None  # Optional stop order update
    type: StopType | None = None  # Optional stop type update
    route_id: int | None = None  # Optional route reassignment (usually not used)

    name: str | None = None  # Optional label update
    address: str | None = None  # Optional address update
    latitude: float | None = None  # Optional latitude update (dragging pin)
    longitude: float | None = None  # Optional longitude update (dragging pin)


# -----------------------------------------------------------
# Schema for returning stop data (GET response)
# -----------------------------------------------------------
class StopOut(BaseModel):
    id: int  # Auto-generated unique ID
    sequence: int  # Stop number on the route
    type: StopType  # pickup/dropoff
    route_id: int  # Linked route ID
    name: str | None = None
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    model_config = ConfigDict(from_attributes=True)


# -----------------------------------------------------------
# Schema for reordering a stop
# -----------------------------------------------------------
class StopReorder(BaseModel):  # Input model
    new_sequence: int  # Target sequence position


# -----------------------------------------------------------
# Stop type enum: pickup or dropoff
# -----------------------------------------------------------
class StopType(str, Enum):
    PICKUP = "pickup"                                 # Pickup stop
    DROPOFF = "dropoff"                               # Dropoff stop


# -----------------------------------------------------------
# Schema for creating a stop (POST request)
# -----------------------------------------------------------
class StopCreate(BaseModel):
    route_id: int                                     # Required route id
    type: str                                         # Required ("pickup" or "dropoff")
    sequence: Optional[int] = None                    # Optional; backend can auto-set
    name: Optional[str] = None                        # Optional stop name
    address: Optional[str] = None                     # Optional address
    planned_time: Optional[time] = None               # Optional scheduled time for running board
    latitude: Optional[float] = None                  # Optional latitude
    longitude: Optional[float] = None                 # Optional longitude


# -----------------------------------------------------------
# Schema for partial stop updates (PATCH request)
# -----------------------------------------------------------
class StopUpdate(BaseModel):
    sequence: int | None = None                       # Optional stop order update
    type: StopType | None = None                      # Optional stop type update
    route_id: int | None = None                       # Optional route reassignment
    name: str | None = None                           # Optional label update
    address: str | None = None                        # Optional address update
    planned_time: time | None = None                  # Optional scheduled time update
    latitude: float | None = None                     # Optional latitude update
    longitude: float | None = None                    # Optional longitude update


# -----------------------------------------------------------
# Schema for returning stop data (GET response)
# -----------------------------------------------------------
class StopOut(BaseModel):
    id: int                                           # Auto-generated unique ID
    sequence: int                                     # True stop order on the route
    type: StopType                                    # pickup/dropoff
    route_id: int                                     # Linked route ID
    name: str | None = None                           # Optional stop label
    address: str | None = None                        # Optional stop address
    planned_time: time | None = None                  # Scheduled time shown on running board
    latitude: float | None = None                     # Optional latitude
    longitude: float | None = None                    # Optional longitude

    model_config = ConfigDict(from_attributes=True)   # ORM → Pydantic support


# -----------------------------------------------------------
# Schema for reordering a stop
# -----------------------------------------------------------
class StopReorder(BaseModel):
    new_sequence: int                                 # Target sequence position