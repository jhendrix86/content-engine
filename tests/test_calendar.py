import uuid
from datetime import datetime, timedelta


async def test_schedule_entry(client):
    r = await client.post("/calendar/schedule", json={
        "title": "Launch post",
        "scheduled_date": (datetime.utcnow() + timedelta(days=1)).isoformat(),
        "platforms": ["twitter", "linkedin"],
    })
    assert r.status_code == 200
    assert r.json()["status"] == "scheduled"
    assert r.json()["platforms"] == ["twitter", "linkedin"]


async def test_get_entry_roundtrip(client):
    created = await client.post("/calendar/schedule", json={
        "title": "A", "scheduled_date": datetime.utcnow().isoformat(), "platforms": ["twitter"],
    })
    entry_id = created.json()["id"]

    r = await client.get(f"/calendar/{entry_id}")
    assert r.status_code == 200
    assert r.json()["id"] == entry_id


async def test_get_nonexistent_entry_returns_404(client):
    r = await client.get(f"/calendar/{uuid.uuid4()}")
    assert r.status_code == 404


async def test_list_entries_filters_by_date_range(client):
    await client.post("/calendar/schedule", json={
        "title": "Past", "scheduled_date": (datetime.utcnow() - timedelta(days=10)).isoformat(),
        "platforms": ["twitter"],
    })
    await client.post("/calendar/schedule", json={
        "title": "Future", "scheduled_date": (datetime.utcnow() + timedelta(days=10)).isoformat(),
        "platforms": ["twitter"],
    })

    r = await client.get("/calendar/", params={"starts_after": datetime.utcnow().isoformat()})
    assert r.json()["total"] == 1
    assert r.json()["entries"][0]["title"] == "Future"


async def test_update_entry(client):
    created = await client.post("/calendar/schedule", json={
        "title": "A", "scheduled_date": datetime.utcnow().isoformat(), "platforms": ["twitter"],
    })
    entry_id = created.json()["id"]

    r = await client.put(f"/calendar/{entry_id}", json={"title": "Updated"})
    assert r.status_code == 200
    assert r.json()["title"] == "Updated"


async def test_skip_entry(client):
    created = await client.post("/calendar/schedule", json={
        "title": "A", "scheduled_date": datetime.utcnow().isoformat(), "platforms": ["twitter"],
    })
    entry_id = created.json()["id"]

    r = await client.post(f"/calendar/{entry_id}/skip")
    assert r.status_code == 200
    assert r.json()["status"] == "skipped"


async def test_delete_entry(client):
    created = await client.post("/calendar/schedule", json={
        "title": "A", "scheduled_date": datetime.utcnow().isoformat(), "platforms": ["twitter"],
    })
    entry_id = created.json()["id"]

    r = await client.delete(f"/calendar/{entry_id}")
    assert r.status_code == 200

    r = await client.get(f"/calendar/{entry_id}")
    assert r.status_code == 404
