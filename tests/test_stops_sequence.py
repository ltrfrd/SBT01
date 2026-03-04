# =============================================================================
# tests/test_stops_sequence.py
# -----------------------------------------------------------------------------
# Stop module transactional behavior:
#   - Append mode (sequence auto = max+1)
#   - Insert mode (block shift)
#   - Reorder (safe shift)
#   - Delete (gap-free normalization)
# =============================================================================


def _create_driver(client):
    r = client.post("/drivers/", json={"name": "T", "email": "t@t.com", "phone": "1"})
    assert r.status_code in (200, 201)
    return r.json()["id"]


def _create_route(client, driver_id: int):
    r = client.post(
        "/routes/",
        json={"route_number": "R1", "unit_number": "Bus-01", "driver_id": driver_id},
    )
    assert r.status_code in (200, 201)
    return r.json()["id"]


def _create_stop(client, route_id: int, name: str, sequence=None):
    payload = {
        "route_id": route_id,
        "name": name,
        "latitude": 40.0,
        "longitude": -70.0,
        "type": "pickup",
    }
    if sequence is not None:
        payload["sequence"] = sequence

    r = client.post("/stops/", json=payload)
    assert r.status_code in (200, 201)
    return r.json()


def _list_stops(client, route_id: int):
    r = client.get("/stops/", params={"route_id": route_id})  # Match router GET /stops?route_id=...
    assert r.status_code == 200
    return r.json()


def test_stop_append_mode_assigns_next_sequence(client):
    driver_id = _create_driver(client)
    route_id = _create_route(client, driver_id)

    s1 = _create_stop(client, route_id, "A")  # No sequence -> append
    s2 = _create_stop(client, route_id, "B")  # No sequence -> append

    assert s1["sequence"] == 1
    assert s2["sequence"] == 2


def test_stop_insert_mode_shifts_block(client):
    driver_id = _create_driver(client)
    route_id = _create_route(client, driver_id)

    _create_stop(client, route_id, "A")
    _create_stop(client, route_id, "B")
    _create_stop(client, route_id, "C")

    _create_stop(client, route_id, "X", sequence=2)  # Insert at 2

    stops = _list_stops(client, route_id)
    names = [s["name"] for s in stops]
    seqs = [s["sequence"] for s in stops]

    assert names == ["A", "X", "B", "C"]
    assert seqs == [1, 2, 3, 4]


def test_stop_reorder_moves_and_shifts(client):
    driver_id = _create_driver(client)
    route_id = _create_route(client, driver_id)

    A = _create_stop(client, route_id, "A")
    B = _create_stop(client, route_id, "B")
    C = _create_stop(client, route_id, "C")
    D = _create_stop(client, route_id, "D")

    # Move D to position 2
    r = client.put(f"/stops/{D['id']}/reorder", json={"new_sequence": 2})
    assert r.status_code == 200

    stops = _list_stops(client, route_id)
    names = [s["name"] for s in stops]
    seqs = [s["sequence"] for s in stops]

    assert names == ["A", "D", "B", "C"]
    assert seqs == [1, 2, 3, 4]


def test_stop_delete_normalizes_gap_free(client):
    driver_id = _create_driver(client)
    route_id = _create_route(client, driver_id)

    A = _create_stop(client, route_id, "A")
    B = _create_stop(client, route_id, "B")
    C = _create_stop(client, route_id, "C")

    r = client.delete(f"/stops/{B['id']}")
    assert r.status_code in (200, 204)

    stops = _list_stops(client, route_id)
    names = [s["name"] for s in stops]
    seqs = [s["sequence"] for s in stops]

    assert names == ["A", "C"]
    assert seqs == [1, 2]