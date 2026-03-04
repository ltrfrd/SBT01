# tests/test_all.py
import sys
import os
import pathlib
import pytest
import json
import time
from fastapi.testclient import TestClient




# =============================================================================
# tests/test_all.py
# -----------------------------------------------------------------------------
# End-to-end API tests (using isolated DB via tests/conftest.py client fixture)
# =============================================================================

# ROOT
def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["status"] == "BST01 backend is running"  # Exact expected status message


# DRIVER CRUD
def test_driver_crud(client):
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


# LOGIN / SESSION
def test_login_logout(client):
    client.post("/drivers/", json={"name": "Login Test", "email": "login@test.com", "phone": "999"})

    r = client.post("/login", json={"driver_id": 1})
    assert r.status_code == 200

    r = client.get("/driver_run/1")
    assert r.status_code == 200

    r = client.post("/logout")
    assert r.status_code == 200

    r = client.get("/driver_run/1")
    assert r.status_code == 401


# WEBSOCKET GPS
def test_websocket_gps(client):
    client.post("/drivers/", json={"name": "D", "email": "d@d.com", "phone": "000"})
    client.post("/login", json={"driver_id": 1})

    # FIX: add route_number
    r = client.post("/routes/", json={"route_number": "R1", "unit_number": "Test", "driver_id": 1})
    assert r.status_code in (200, 201)
    route_id = r.json()["id"]

    r = client.post("/runs/start", json={"driver_id": 1, "route_id": route_id, "run_type": "AM"})
    assert r.status_code in (200, 201)
    run_id = r.json()["id"]

    with client.websocket_connect(f"/ws/gps/{run_id}") as ws:
        ws.send_json({"lat": 40.7128, "lng": -74.0060})
        data = ws.receive_json()
        assert data["run_id"] == run_id
        assert "progress" in data


# ALERTS
def test_alerts(client):
    r = client.post("/drivers/", json={"name": "Driver", "email": "d@d.com", "phone": "000"})
    assert r.status_code in (200, 201)
    driver_id = r.json()["id"]

    client.post("/login", json={"driver_id": driver_id})

    # FIX: add route_number
    r = client.post("/routes/", json={"route_number": "R1", "unit_number": "Bus-01", "driver_id": driver_id})
    assert r.status_code in (200, 201)
    route_id = r.json()["id"]
    
    # Create a school (required by StudentCreate: school_id)
    r = client.post(
    "/schools/",
    json={
        "name": "Test School",
        "address": "123 Test St",  # Required field
    },
)
    assert r.status_code in (200, 201) # Show validation error if 422
    school_id = r.json()["id"]

    r = client.post(
        "/stops/",
        json={
            "name": "Park",
            "latitude": 40.7580,
            "longitude": -73.9855,
            "type": "pickup",
            "route_id": route_id,
            "sequence": 1,
        },
    )
    assert r.status_code in (200, 201)
    stop_id = r.json()["id"]

    r = client.post(
    "/students/",
    json={
        "name": "Kid",
        "school_id": school_id,  # Required field
        "stop_id": stop_id,
        "notification_distance_meters": 100,
    },
)
    assert r.status_code in (200, 201)
    
    r = client.post("/runs/start", json={"driver_id": driver_id, "route_id": route_id, "run_type": "AM"})
    assert r.status_code in (200, 201)
    run_id = r.json()["id"]

    with client.websocket_connect(f"/ws/gps/{run_id}") as ws:
        ws.send_json({"lat": 40.7580, "lng": -73.9855})
        data = ws.receive_json()
        assert "progress" in data