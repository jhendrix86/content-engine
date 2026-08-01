import uuid


async def test_generate_content_calls_real_ai_writer(client):
    """No API key is configured in tests, so this proves the router really
    calls AIWriter (real error) rather than faking generated copy."""
    r = await client.post("/content/generate", json={
        "title": "Why Widgets Matter",
        "content_type": "blog_post",
        "topic": "widgets",
    })
    assert r.status_code == 200
    content = r.json()
    assert content["status"] == "draft"  # generation failed -> stays draft, not faked as ready
    assert content["extra_metadata"]["generation_result"]["success"] is False
    assert "OpenAI API key not configured" in content["extra_metadata"]["generation_result"]["error"]


async def test_get_content_roundtrip(client):
    created = await client.post("/content/generate", json={
        "title": "A", "content_type": "blog_post", "topic": "a",
    })
    content_id = created.json()["id"]

    r = await client.get(f"/content/{content_id}")
    assert r.status_code == 200
    assert r.json()["id"] == content_id


async def test_get_nonexistent_content_returns_404(client):
    r = await client.get(f"/content/{uuid.uuid4()}")
    assert r.status_code == 404


async def test_list_content_filters_by_type(client):
    await client.post("/content/generate", json={"title": "A", "content_type": "blog_post", "topic": "a"})
    await client.post("/content/generate", json={"title": "B", "content_type": "social_media", "topic": "b"})

    r = await client.get("/content/", params={"content_type": "blog_post"})
    assert r.json()["total"] == 1


async def test_update_content(client):
    created = await client.post("/content/generate", json={
        "title": "A", "content_type": "blog_post", "topic": "a",
    })
    content_id = created.json()["id"]

    r = await client.put(f"/content/{content_id}", json={"body": "edited body", "status": "ready"})
    assert r.status_code == 200
    assert r.json()["body"] == "edited body"
    assert r.json()["status"] == "ready"


async def test_publish_content_sets_published_at(client):
    created = await client.post("/content/generate", json={
        "title": "A", "content_type": "blog_post", "topic": "a",
    })
    content_id = created.json()["id"]

    r = await client.post(f"/content/{content_id}/publish")
    assert r.status_code == 200
    assert r.json()["status"] == "published"
    assert r.json()["published_at"] is not None


async def test_delete_content(client):
    created = await client.post("/content/generate", json={
        "title": "A", "content_type": "blog_post", "topic": "a",
    })
    content_id = created.json()["id"]

    r = await client.delete(f"/content/{content_id}")
    assert r.status_code == 200

    r = await client.get(f"/content/{content_id}")
    assert r.status_code == 404
