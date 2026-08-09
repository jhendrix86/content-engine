import uuid

import httpx
import respx


async def _make_content(client):
    created = await client.post("/content/generate", json={
        "title": "A", "content_type": "blog_post", "topic": "a",
    })
    return created.json()["id"]


async def test_publish_records_a_real_distribution_row(client):
    content_id = await _make_content(client)

    r = await client.post("/distribution/publish", json={"content_id": content_id, "platform": "twitter"})
    assert r.status_code == 200
    assert r.json()["status"] == "pending"
    assert r.json()["platform"] == "twitter"


async def test_publish_with_scheduled_at_marks_scheduled(client):
    content_id = await _make_content(client)

    r = await client.post("/distribution/publish", json={
        "content_id": content_id, "platform": "linkedin", "scheduled_at": "2027-01-01T00:00:00",
    })
    assert r.json()["status"] == "scheduled"


async def test_publish_for_nonexistent_content_returns_404(client):
    r = await client.post("/distribution/publish", json={
        "content_id": str(uuid.uuid4()), "platform": "twitter",
    })
    assert r.status_code == 404


async def test_execute_is_honest_about_no_platform_client(client):
    content_id = await _make_content(client)
    created = await client.post("/distribution/publish", json={"content_id": content_id, "platform": "twitter"})
    distribution_id = created.json()["id"]

    r = await client.post(f"/distribution/{distribution_id}/execute")
    assert r.status_code == 200
    assert r.json()["status"] == "failed"
    assert "No platform posting client exists for 'twitter'" in r.json()["error"]


async def test_execute_is_honest_when_wordpress_not_configured(client, monkeypatch):
    import app.config as config_module
    monkeypatch.setattr(config_module.settings, "wordpress_url", "")

    content_id = await _make_content(client)
    created = await client.post("/distribution/publish", json={"content_id": content_id, "platform": "wordpress"})
    distribution_id = created.json()["id"]

    r = await client.post(f"/distribution/{distribution_id}/execute")
    assert r.status_code == 200
    assert r.json()["status"] == "failed"
    assert "not configured" in r.json()["error"]


@respx.mock
async def test_execute_publishes_for_real_when_wordpress_is_configured(client, monkeypatch):
    import app.config as config_module
    monkeypatch.setattr(config_module.settings, "wordpress_url", "https://example.com")
    monkeypatch.setattr(config_module.settings, "wordpress_username", "admin")
    monkeypatch.setattr(config_module.settings, "wordpress_app_password", "app-pass")

    respx.post("https://example.com/wp-json/wp/v2/posts").mock(
        return_value=httpx.Response(201, json={"id": 7, "link": "https://example.com/?p=7"})
    )

    content_id = await _make_content(client)
    created = await client.post("/distribution/publish", json={"content_id": content_id, "platform": "wordpress"})
    distribution_id = created.json()["id"]

    r = await client.post(f"/distribution/{distribution_id}/execute")

    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "published"
    assert body["platform_post_id"] == "7"


async def test_list_distributions_filters_by_platform(client):
    content_id = await _make_content(client)
    await client.post("/distribution/publish", json={"content_id": content_id, "platform": "twitter"})
    await client.post("/distribution/publish", json={"content_id": content_id, "platform": "linkedin"})

    r = await client.get("/distribution/", params={"platform": "twitter"})
    assert r.json()["total"] == 1
