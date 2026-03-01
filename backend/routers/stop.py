# ===========================================================
# backend/routers/stop.py — BST Stop Router
# -----------------------------------------------------------
# Handles CRUD for bus stops (pickup/dropoff) per route.
# ===========================================================
from fastapi import APIRouter, Depends, HTTPException, status  # FastAPI imports
from sqlalchemy.orm import Session  # SQLAlchemy session
from typing import List  # For type hinting lists
from database import get_db  # DB dependency
from backend import schemas  # Stop schemas
from backend.models import stop as stop_model  # Stop model
from backend.models import route as route_model  # Route model (FK validation)
from sqlalchemy import func                              # For MAX() query
from fastapi import HTTPException                        # For clean API errors
from backend.schemas.stop import StopCreate, StopOut
from backend.models.stop import Stop
from sqlalchemy.exc import IntegrityError  # Catch database constraint violations (UNIQUE, FK, etc.)
from backend.utils.db_errors import raise_conflict_if_unique  # Convert UNIQUE violations to HTTP 409

# -----------------------------------------------------------
# Normalize sequences for a single route (gap-free 1..N)
# - Keeps existing order (by current sequence ASC)
# - Uses 2-phase shift to avoid UNIQUE(route_id, sequence) collisions
# -----------------------------------------------------------
def normalize_route_sequences(db: Session, route_id: int) -> None:
    OFFSET = 100000                                     # Large offset to move rows into a safe, non-colliding range

    # 1) Load all stops for this route in current order
    stops = (
        db.query(Stop)                                  # Query Stop table
        .filter(Stop.route_id == route_id)              # Only stops for the given route
        .order_by(Stop.sequence.asc())                  # Preserve current ordering by sequence
        .all()                                          # Materialize list
    )

    # 2) If no stops, nothing to normalize
    if not stops:                                       # Empty route => no work
        return                                          # Exit early

    # 3) Build desired mapping: stable 1..N in same order
    desired_by_id = {}                                  # stop_id -> new_sequence
    for idx, s in enumerate(stops):                     # Walk stops in current sequence order
        desired_by_id[s.id] = idx + 1                   # Assign normalized sequence starting at 1

    # 4) Fast exit if already normalized
    already_ok = True                                   # Assume OK until proven otherwise
    for s in stops:                                     # Check each stop
        if s.sequence != desired_by_id[s.id]:           # If any stop has a gap or mismatch
            already_ok = False                          # Mark as not normalized
            break                                       # Stop checking
    if already_ok:                                      # If all sequences already 1..N
        return                                          # Nothing to do

    # 5) Phase 1: move all sequences to a safe zone (sequence + OFFSET)
    for s in stops:                                     # For each stop
        s.sequence = s.sequence + OFFSET                 # Shift into safe zone to avoid unique collisions
    db.flush()                                          # Flush phase 1 to DB so phase 2 is safe

    # 6) Phase 2: write final normalized sequences (1..N)
    for s in stops:                                     # For each stop again
        s.sequence = desired_by_id[s.id]                # Set exact normalized value
    db.flush()                                          # Flush final normalized values# -----------------------------------------------------------

# -----------------------------------------------------------
# Router setup
# -----------------------------------------------------------
router = APIRouter(
    prefix="/stops",  # All endpoints under /stops
    tags=["Stops"]    # Swagger group label
)

# -----------------------------------------------------------
# POST /stops → Create stop (append or insert)
# - Append Mode: if sequence missing → MAX(sequence)+1
# - Insert Mode: if sequence provided → clamp + shift (2-phase) + insert
# -----------------------------------------------------------
@router.post("/", response_model=StopOut, status_code=201)                          # Create stop endpoint
def create_stop(payload: StopCreate, db: Session = Depends(get_db)):               # Inject DB session

    try:                                                                           # Start protected DB operation

        # -----------------------------------------------------------
        # Read current max sequence for this route (used by both modes)
        # -----------------------------------------------------------
        max_seq = (                                                                # Calculate current max sequence
            db.query(func.max(stop_model.Stop.sequence))                           # SELECT MAX(sequence)
            .filter(stop_model.Stop.route_id == payload.route_id)                  # WHERE route_id = X
            .scalar()                                                             # Return scalar value
        )
        max_seq = max_seq or 0                                                     # If no stops exist yet, treat as 0

        # -----------------------------------------------------------
        # Mode 1: Append Mode (client omitted sequence)
        # -----------------------------------------------------------
        if payload.sequence is None:                                               # If client did not send sequence
            seq = max_seq + 1                                                      # Append to end (max+1)

        # -----------------------------------------------------------
        # Mode 2: Insert Mode (client provided sequence)
        # -----------------------------------------------------------
        else:
            target = payload.sequence                                              # Requested insert position
            target = max(1, min(target, max_seq + 1))                              # Clamp into valid range [1..max+1]

            OFFSET = 100000                                                        # Big offset to avoid UNIQUE collisions

            # -----------------------------------------------------------
            # Phase 1: move impacted rows to safe zone (sequence + OFFSET)
            # - We move only stops in same route with sequence >= target
            # - Descending order helps keep deterministic shifting
            # -----------------------------------------------------------
            impacted = (                                                           # Load impacted stops
                db.query(stop_model.Stop)                                          # Query Stop model
                .filter(stop_model.Stop.route_id == payload.route_id)              # Same route only
                .filter(stop_model.Stop.sequence >= target)                        # Stops at/after target
                .order_by(stop_model.Stop.sequence.desc())                         # Desc order for safe updates
                .all()                                                             # Materialize list
            )

            for s in impacted:                                                     # For each impacted stop
                s.sequence = s.sequence + OFFSET                                   # Push into safe zone
            db.flush()                                                             # Flush phase 1 to prevent collisions

            # -----------------------------------------------------------
            # Phase 2: move them back to final position (+1)
            # -----------------------------------------------------------
            for s in impacted:                                                     # For each impacted stop again
                s.sequence = (s.sequence - OFFSET) + 1                              # Restore then shift by 1
            db.flush()                                                             # Flush phase 2 updates

            seq = target                                                           # New stop takes the target slot

        # -----------------------------------------------------------
        # Create stop record (force computed sequence)
        # -----------------------------------------------------------
        data = payload.model_dump()                                                # Convert payload to dict
        data["sequence"] = seq                                                     # Force final sequence into dict

        stop = stop_model.Stop(**data)                                             # Build ORM object
        db.add(stop)                                                               # Add to session
        db.commit()                                                                # Commit once (atomic)
        db.refresh(stop)                                                           # Refresh to load generated fields
        return stop                                                                # Return created stop

    except IntegrityError as e:                                                    # Catch DB constraint errors
        db.rollback()                                                              # Roll back transaction safely
        raise_conflict_if_unique(e)                                                # Convert UNIQUE(route_id, sequence) to 409
        raise HTTPException(status_code=400, detail="Integrity error")              # Other integrity issues

# -----------------------------------------------------------
# GET /stops → List stops (optionally filter by route_id)
# Always ordered by sequence ascending
# -----------------------------------------------------------
@router.get("/", response_model=List[schemas.StopOut])
def get_stops(route_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(stop_model.Stop)                         # Base query

    if route_id is not None:                                  # If filtering by route
        query = query.filter(stop_model.Stop.route_id == route_id)  # Apply route filter

    query = query.order_by(stop_model.Stop.sequence.asc())    # Ensure stops ordered by sequence

    return query.all()                                        # Return ordered results
# -----------------------------------------------------------
# PUT /stops/{stop_id} → Update stop info
# -----------------------------------------------------------
@router.put("/{stop_id}", response_model=schemas.StopOut)
def update_stop(stop_id: int, stop_in: schemas.StopUpdate, db: Session = Depends(get_db)):
    stop = db.get(stop_model.Stop, stop_id)                      # Load stop from DB
    if not stop:                                                 # If stop does not exist
        raise HTTPException(status_code=404, detail="Stop not found")

    updates = stop_in.model_dump(exclude_none=True)              # Only apply provided fields
    for key, value in updates.items():                           # Loop through fields
        setattr(stop, key, value)                                # Update stop attributes

    db.commit()                                                  # Save changes
    db.refresh(stop)                                             # Refresh instance
    return stop                                                  # Return updated stop
# -----------------------------------------------------------
# DELETE /stops/{stop_id} → Remove stop
# - Deletes stop
# - Normalizes remaining stops to keep sequences gap-free
# -----------------------------------------------------------
@router.delete("/{stop_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_stop(stop_id: int, db: Session = Depends(get_db)):
    """Delete a stop record and normalize route sequence."""

    try:                                                       # Begin protected transaction block

        stop = db.get(stop_model.Stop, stop_id)               # Fetch stop by primary key
        if not stop:                                          # If stop does not exist
            raise HTTPException(status_code=404, detail="Stop not found")  # Return 404

        route_id = stop.route_id                              # Save route_id before deletion

        db.delete(stop)                                       # Mark stop for deletion
        db.flush()                                            # Apply deletion before renumbering

        normalize_route_sequences(db, route_id)               # Reassign sequences 1..N for this route

        db.commit()                                           # Commit entire operation atomically

        return None                                           # 204 No Content response

    except IntegrityError as e:                               # Catch DB constraint issues
        db.rollback()                                         # Roll back transaction safely
        raise_conflict_if_unique(e)                           # Convert UNIQUE violations to HTTP 409
        raise HTTPException(status_code=400, detail="Integrity error")  # Other DB errors → 400
    
    # -----------------------------------------------------------
# PUT /stops/{stop_id}/reorder → Move stop to new position
# -----------------------------------------------------------
@router.put("/{stop_id}/reorder", response_model=StopOut)
def reorder_stop(stop_id: int, payload: schemas.StopReorder, db: Session = Depends(get_db)):

    try:                                                                    # Protected transaction

        stop = db.get(stop_model.Stop, stop_id)                             # Load stop
        if not stop:                                                        # If not found
            raise HTTPException(status_code=404, detail="Stop not found")

        route_id = stop.route_id                                            # Save route id
        old_seq = stop.sequence                                             # Save current position

        # Get current max sequence in route
        max_seq = (
            db.query(func.max(stop_model.Stop.sequence))
            .filter(stop_model.Stop.route_id == route_id)
            .scalar()
        ) or 0

        # Clamp target position into valid range
        new_seq = max(1, min(payload.new_sequence, max_seq))

        if new_seq == old_seq:                                              # If nothing changes
            return stop                                                     # No operation needed

        OFFSET = 100000                                                     # Safe offset

        # Phase 1: temporarily move current stop out of range
        stop.sequence = stop.sequence + OFFSET
        db.flush()

        if new_seq < old_seq:
            # Moving upward (e.g., 5 → 2)
            impacted = (
                db.query(stop_model.Stop)
                .filter(stop_model.Stop.route_id == route_id)
                .filter(stop_model.Stop.sequence >= new_seq)
                .filter(stop_model.Stop.sequence < old_seq + OFFSET)
                .all()
            )
            for s in impacted:
                s.sequence += 1

        else:
            # Moving downward (e.g., 2 → 5)
            impacted = (
                db.query(stop_model.Stop)
                .filter(stop_model.Stop.route_id == route_id)
                .filter(stop_model.Stop.sequence > old_seq)
                .filter(stop_model.Stop.sequence <= new_seq)
                .all()
            )
            for s in impacted:
                s.sequence -= 1

        stop.sequence = new_seq                                             # Place stop at new position
        db.commit()
        db.refresh(stop)
        return stop

    except IntegrityError as e:
        db.rollback()
        raise_conflict_if_unique(e)
        raise HTTPException(status_code=400, detail="Integrity error")