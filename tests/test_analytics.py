import uuid


async def _make_content(client):
    created = await client.post("/content/generate", json={
        "title": "A", "content_type": "blog_post", "topic": "a",
    })
    return created.json()["id"]


async def test_overview_reflects_real_counts(client):
    await _make_content(client)
    await _make_content(client)

    r = await client.get("/analytics/overview")
    assert r.status_code == 200
    overview = r.json()
    assert overview["total_content"] == 2
    assert overview["content_by_type"]["blog_post"] == 2


async def test_track_event_updates_real_counters(client):
    content_id = await _make_content(client)

    r = await client.post(f"/analytics/content/{content_id}/track", json={
        "views": 100, "engagements": 10, "conversions": 2,
    })
    assert r.status_code == 200
    assert r.json()["views"] == 100

    # tracking again should accumulate, not overwrite
    r = await client.post(f"/analytics/content/{content_id}/track", json={"views": 50})
    assert r.json()["views"] == 150


async def test_content_performance_includes_conversion_rate(client):
    content_id = await _make_content(client)
    await client.post(f"/analytics/content/{content_id}/track", json={"views": 200, "conversions": 10})

    r = await client.get(f"/analytics/content/{content_id}/performance")
    assert r.status_code == 200
    assert r.json()["conversion_rate_percent"] == 5.0


async def test_performance_for_nonexistent_content_returns_404(client):
    r = await client.get(f"/analytics/content/{uuid.uuid4()}/performance")
    assert r.status_code == 404
