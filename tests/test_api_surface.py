# =============================================================================
# tests/test_api_surface.py
# -----------------------------------------------------------------------------
# Broad API coverage (CRUD + basic invariants)
# Uses the isolated DB + client fixture from tests/conftest.py
# =============================================================================


from tests.conftest import client


def test_schools_crud(client):
    # Create
    r = client.post("/schools/", json={"name": "S1", "address": "1 Main St"})
    assert r.status_code in (200, 201)
    school_id = r.json()["id"]

    # List
    r = client.get("/schools/")
    assert r.status_code == 200
    assert any(s["id"] == school_id for s in r.json())

    # Get
    r = client.get(f"/schools/{school_id}")
    assert r.status_code == 200
    assert r.json()["name"] == "S1"

    # Update
    # Update (SchoolUpdate appears to require full payload, not partial)
    r = client.put(
        f"/schools/{school_id}",
        json={
            "name": "S1-updated",
            "address": "1 Main St",  # Keep required field for full update
        },
    )
    assert r.status_code == 200
    assert r.json()["name"] == "S1-updated"
    
    # Delete
    r = client.delete(f"/schools/{school_id}")
    assert r.status_code in (200, 204)
    r = client.get(f"/schools/{school_id}")
    assert r.status_code == 404


def test_routes_crud(client):
    # Driver required for routes
    r = client.post("/drivers/", json={"name": "D1", "email": "d1@x.com", "phone": "1"})
    assert r.status_code in (200, 201)
    driver_id = r.json()["id"]

    # Create route
    r = client.post("/routes/", json={"route_number": "R100", "unit_number": "Bus-100", "driver_id": driver_id})
    assert r.status_code in (200, 201)
    route_id = r.json()["id"]

    # List
    r = client.get("/routes/")
    assert r.status_code == 200
    assert any(rt["id"] == route_id for rt in r.json())

    # Get
    r = client.get(f"/routes/{route_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == route_id  # Must match
    assert "unit_number" in data   # Verify key exists  

    # Update
    # Update (RouteUpdate appears to require full payload, not partial)
    r = client.put(
        f"/routes/{route_id}",
        json={
            "route_number": "R100",      # Required field
            "unit_number": "Bus-101",    # Updated field
            "driver_id": driver_id,      # Required field
        },
    )
    assert r.status_code == 200
    assert r.json()["unit_number"] == "Bus-101"
    # Delete
    r = client.delete(f"/routes/{route_id}")
    assert r.status_code in (200, 204)
    r = client.get(f"/routes/{route_id}")
    assert r.status_code == 404


def test_students_crud(client):
    # Need a school and stop
    r = client.post("/schools/", json={"name": "S1", "address": "1 Main St"})
    assert r.status_code in (200, 201)
    school_id = r.json()["id"]

    r = client.post("/drivers/", json={"name": "D1", "email": "d1@x.com", "phone": "1"})
    assert r.status_code in (200, 201)
    driver_id = r.json()["id"]

    r = client.post("/routes/", json={"route_number": "R1", "unit_number": "Bus-01", "driver_id": driver_id})
    assert r.status_code in (200, 201)
    route_id = r.json()["id"]

    r = client.post("/stops/", json={"route_id": route_id, "name": "Stop1", "latitude": 1, "longitude": 1, "type": "pickup"})
    assert r.status_code in (200, 201)
    stop_id = r.json()["id"]

    # Create student
    r = client.post("/students/", json={"name": "Kid1", "school_id": school_id, "stop_id": stop_id, "notification_distance_meters": 100})
    assert r.status_code in (200, 201)
    student_id = r.json()["id"]

    # List
    r = client.get("/students/")
    assert r.status_code == 200
    assert any(s["id"] == student_id for s in r.json())

    # Get
    r = client.get(f"/students/{student_id}")
    assert r.status_code == 200
    assert r.json()["name"] == "Kid1"

    # Update
    # Update (StudentUpdate appears to require full payload, not partial)
    r = client.put(
        f"/students/{student_id}",
        json={
            "name": "Kid1-updated",
            "school_id": school_id,                         # Required
            "stop_id": stop_id,                             # Required
            "notification_distance_meters": 100,            # Required
        },
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Kid1-updated"

    # Delete
    r = client.delete(f"/students/{student_id}")
    assert r.status_code in (200, 204)
    r = client.get(f"/students/{student_id}")
    assert r.status_code == 404