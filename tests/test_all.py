# tests/test_all.py
import sys
import os
import pathlib
import pytest
import json
import time
from fastapi.testclient import TestClient

# PATH FIX
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, get_db
from database import SessionLocal, Base, engine


# -----------------------------------------------------------
# CLIENT SETUP
# -----------------------------------------------------------
client = TestClient(app)


# -----------------------------------------------------------
# YOUR PERFECT FIXTURE — SAFE DB RESET
# -----------------------------------------------------------
# -----------------------------------------------------------
# FIXTURE — BULLETPROOF DB RESET
# -----------------------------------------------------------
@pytest.fixture(autouse=True)
def setup_db():
    """Safely reset sbt.db before each test — handles locked files."""
    from sqlalchemy import inspect

    # Close all connections
    engine.dispose()

    db_path = pathlib.Path("sbt.db")
    if db_path.exists():
        try:
            os.remove(db_path)
        except PermissionError:
            # Fallback: rename to .bak (works on locked files)
            backup_path = db_path.with_suffix(".bak")
            if backup_path.exists():
                backup_path.unlink()  # Remove old backup
            os.rename(db_path, backup_path)

    # Recreate tables
    Base.metadata.create_all(bind=engine)
    yield

    # Cleanup
    Base.metadata.drop_all(bind=engine)
    engine.dispose()

    # Optional: delete backup after test
    backup_path = pathlib.Path("sbt.db.bak")
    if backup_path.exists():
        try:
            backup_path.unlink()
        except:
            pass  # OK if still locked

# -----------------------------------------------------------
# OVERRIDE DB DEPENDENCY
# -----------------------------------------------------------
def override_get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db


# -----------------------------------------------------------
# 1. ROOT ENDPOINT
# -----------------------------------------------------------
def test_root():
    r = client.get("/")
    assert r.status_code == 200
    assert "BST backend" in r.text


# -----------------------------------------------------------
# 2. DRIVER CRUD
# -----------------------------------------------------------
def test_driver_crud():
    payload = {"name": "John Doe", "email": "john@example.com", "phone": "12345"}
    r = client.post("/drivers/", json=payload)
    assert r.status_code in (200, 201)
    driver_id = r.json()["id"]

    r = client.get("/drivers/")
    assert r.status_code == 200
    assert any(d["name"] == "John Doe" for d in r.json())

    r = client.get(f"/drivers/{driver_id}")
    assert r.status_code == 200

    r = client.put(f"/drivers/{driver_id}", json={"name": "Jane Doe"})
    assert r.status_code == 200

    r = client.delete(f"/drivers/{driver_id}")
    assert r.status_code in (200, 204)
    r = client.get(f"/drivers/{driver_id}")
    assert r.status_code == 404


# -----------------------------------------------------------
# 3. LOGIN / SESSION
# -----------------------------------------------------------
def test_login_logout():
    client.post("/drivers/", json={"name": "Login Test", "email": "login@test.com", "phone": "999"})
    r = client.post("/login", json={"driver_id": 1})
    assert r.status_code == 200

    r = client.get("/driver_run/1")
    assert r.status_code == 200

    r = client.post("/logout")
    assert r.status_code == 200

    r = client.get("/driver_run/1")
    assert r.status_code == 401


# -----------------------------------------------------------
# 4. WEBSOCKET GPS
# -----------------------------------------------------------
def test_websocket_gps():
    with TestClient(app) as client:
        # Setup run
        client.post("/drivers/", json={"name": "D", "email": "d@d.com", "phone": "000"})
        client.post("/login", json={"driver_id": 1})
        r = client.post("/routes/", json={"unit_number": "Test", "driver_id": 1})
        route_id = r.json()["id"]
        r = client.post("/runs/start", json={"driver_id": 1, "route_id": route_id, "run_type": "AM"})
        run_id = r.json()["id"]

        with client.websocket_connect(f"/ws/gps/{run_id}") as ws:
            ws.send_json({"lat": 40.7128, "lng": -74.0060})
            data = ws.receive_json()
            assert data["run_id"] == run_id
            assert "progress" in data


# -----------------------------------------------------------
# 5. ALERTS
# -----------------------------------------------------------
def test_alerts():
    with TestClient(app) as client:
        # Driver
        r = client.post("/drivers/", json={"name": "Driver", "email": "d@d.com", "phone": "000"})
        driver_id = r.json()["id"]
        client.post("/login", json={"driver_id": driver_id})

        # Route
        r = client.post("/routes/", json={"unit_number": "Bus-01", "driver_id": driver_id})
        route_id = r.json()["id"]

        # Stop
        r = client.post("/stops/", json={
            "name": "Park", "latitude": 40.7580, "longitude": -73.9855,
            "type": "pickup", "route_id": route_id, "sequence": 1
        })
        stop_id = r.json()["id"]

        # Student
        client.post("/students/", json={
            "name": "Kid", "stop_id": stop_id, "notification_distance_meters": 100
        })

        # Start Run
        r = client.post("/runs/start", json={"driver_id": driver_id, "route_id": route_id, "run_type": "AM"})
        run_id = r.json()["id"]

        # GPS
        with client.websocket_connect(f"/ws/gps/{run_id}") as ws:
            ws.send_json({"lat": 40.7580, "lng": -73.9855})
            data = ws.receive_json()
            assert "progress" in data