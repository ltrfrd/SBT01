# =============================================================================
# tests/test_stops_edge_cases.py
# -----------------------------------------------------------------------------
# Stop edge cases:
#   - Unique constraint produces 409
#   - Insert clamps to [1..max+1]
#   - Admin endpoints are gated (403 without token)
# =============================================================================


def _setup_route(client):
    r = client.post("/drivers/", json={"name": "D", "email": "d@d.com", "phone": "1"})
    assert r.status_code in (200, 201)
    driver_id = r.json()["id"]

    r = client.post("/routes/", json={"route_number": "R1", "unit_number": "Bus-01", "driver_id": driver_id})
    assert r.status_code in (200, 201)
    return r.json()["id"]


def test_stop_insert_same_sequence_shifts_and_remains_unique(client):
    route_id = _setup_route(client)

    r = client.post("/stops/", json={
        "route_id": route_id, "name": "A", "latitude": 1, "longitude": 1, "type": "pickup", "sequence": 1
    })
    assert r.status_code in (200, 201)

    # Insert again at sequence=1 -> should succeed by shifting existing stop(s)
    r = client.post("/stops/", json={
        "route_id": route_id, "name": "B", "latitude": 2, "longitude": 2, "type": "pickup", "sequence": 1
    })
    assert r.status_code in (200, 201)

    # Verify uniqueness + order
    r = client.get("/stops/", params={"route_id": route_id})
    assert r.status_code == 200
    stops = r.json()

    seqs = [s["sequence"] for s in stops]
    names = [s["name"] for s in stops]

    assert seqs == [1, 2]
    assert names == ["B", "A"]  # B inserted at 1, A shifted to 2
    assert len(seqs) == len(set(seqs))  # No duplicates


def test_stop_insert_clamps_sequence(client):
    route_id = _setup_route(client)

    client.post("/stops/", json={"route_id": route_id, "name": "A", "latitude": 1, "longitude": 1, "type": "pickup"})
    client.post("/stops/", json={"route_id": route_id, "name": "B", "latitude": 2, "longitude": 2, "type": "pickup"})

    # Too low -> clamp to 1
    r = client.post("/stops/", json={"route_id": route_id, "name": "X", "latitude": 3, "longitude": 3, "type": "pickup", "sequence": -50})
    assert r.status_code in (200, 201)

    # List by route_id param (your real endpoint)
    r = client.get("/stops/", params={"route_id": route_id})
    assert r.status_code == 200
    seqs = [s["sequence"] for s in r.json()]
    assert seqs == sorted(seqs)
    assert seqs[0] == 1  # starts at 1 after clamp/normalize behavior


def test_admin_endpoints_require_token(client):
    route_id = _setup_route(client)

    r = client.get(f"/stops/validate/{route_id}")
    assert r.status_code == 403

    r = client.post(f"/stops/normalize/{route_id}")
    assert r.status_code == 403