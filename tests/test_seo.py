import uuid


async def _make_content_with_body(client, body, title="A great article about widgets"):
    created = await client.post("/content/generate", json={
        "title": title, "content_type": "blog_post", "topic": "widgets",
    })
    content_id = created.json()["id"]
    await client.put(f"/content/{content_id}", json={"body": body, "summary": "A short summary."})
    return content_id


async def test_analyze_computes_real_scores(client):
    body = (
        "Widgets are great. Widgets help you get things done. "
        "This article explains why widgets matter for your business.\n\n"
        "Widgets save time. Widgets save money. Everyone loves a good widget.\n\n"
        "In conclusion, widgets are the best tool for the job."
    )
    content_id = await _make_content_with_body(client, body)

    r = await client.post("/seo/analyze", json={"content_id": content_id, "primary_keyword": "widgets"})
    assert r.status_code == 200
    analysis = r.json()
    assert 0 <= analysis["overall_score"] <= 100
    assert 0 <= analysis["readability_score"] <= 100
    assert analysis["primary_keyword"] == "widgets"
    assert isinstance(analysis["recommendations"], list) and len(analysis["recommendations"]) > 0


async def test_analyze_without_body_returns_400(client):
    created = await client.post("/content/generate", json={
        "title": "Empty", "content_type": "blog_post", "topic": "x",
    })
    content_id = created.json()["id"]

    r = await client.post("/seo/analyze", json={"content_id": content_id})
    assert r.status_code == 400


async def test_analyze_nonexistent_content_returns_404(client):
    r = await client.post("/seo/analyze", json={"content_id": str(uuid.uuid4())})
    assert r.status_code == 404


async def test_get_analysis_returns_most_recent(client):
    content_id = await _make_content_with_body(client, "Some words here. More words here.")
    await client.post("/seo/analyze", json={"content_id": content_id})

    r = await client.get(f"/seo/{content_id}")
    assert r.status_code == 200
    assert r.json()["content_id"] == content_id


async def test_get_analysis_for_unanalyzed_content_returns_404(client):
    content_id = await _make_content_with_body(client, "Some words here.")
    r = await client.get(f"/seo/{content_id}")
    assert r.status_code == 404


async def test_track_and_list_keywords(client):
    r = await client.post("/seo/keywords", json={"keyword": "widgets", "search_volume": 1000})
    assert r.status_code == 200
    assert r.json()["keyword"] == "widgets"

    r = await client.get("/seo/keywords/list")
    assert r.json()["total"] == 1
