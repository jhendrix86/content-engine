import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.main import app as fastapi_app


async def _make_content_with_body(client, body="Pillar content body about widgets."):
    created = await client.post("/content/generate", json={
        "title": "Widgets 101", "content_type": "blog_post", "topic": "widgets",
    })
    content_id = created.json()["id"]
    # /generate leaves body empty with no API key configured in tests; set it directly.
    await client.put(f"/content/{content_id}", json={"body": body})
    return content_id


def _install_fake_openai_client(fake_body="Repurposed social post!"):
    """Swap the live app's AIWriter._client for a fake with the same async interface."""
    fake_response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=fake_body))]
    )
    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock(return_value=fake_response)))
    )
    fastapi_app.state.ai_writer._client = fake_client
    return fake_client


async def test_repurpose_without_openai_configured_creates_honest_draft(client):
    content_id = await _make_content_with_body(client)

    r = await client.post(f"/content/{content_id}/repurpose", json={"target_types": ["social_media"]})

    assert r.status_code == 200
    body = r.json()
    assert body["source_content_id"] == content_id
    derivative = body["derivatives"][0]
    assert derivative["content_type"] == "social_media"
    assert derivative["status"] == "draft"
    assert derivative["source_content_id"] == content_id
    assert "OpenAI API key not configured" in derivative["extra_metadata"]["generation_result"]["error"]


async def test_repurpose_for_nonexistent_content_returns_404(client):
    r = await client.post(f"/content/{uuid.uuid4()}/repurpose", json={"target_types": ["social_media"]})
    assert r.status_code == 404


async def test_repurpose_without_body_returns_400(client):
    created = await client.post("/content/generate", json={
        "title": "Empty", "content_type": "blog_post", "topic": "empty",
    })
    content_id = created.json()["id"]

    r = await client.post(f"/content/{content_id}/repurpose", json={"target_types": ["social_media"]})
    assert r.status_code == 400


async def test_repurpose_generates_real_derivatives_across_multiple_types(client):
    content_id = await _make_content_with_body(client)
    fake_client = _install_fake_openai_client(fake_body="Repurposed copy!")

    r = await client.post(f"/content/{content_id}/repurpose", json={
        "target_types": ["social_media", "email_copy", "video_script"]
    })

    assert r.status_code == 200
    body = r.json()
    derivatives = body["derivatives"]
    assert len(derivatives) == 3
    assert {d["content_type"] for d in derivatives} == {"social_media", "email_copy", "video_script"}
    for d in derivatives:
        assert d["status"] == "ready"
        assert d["body"] == "Repurposed copy!"
        assert d["source_content_id"] == content_id
    assert fake_client.chat.completions.create.call_count == 3


async def test_list_derivatives_returns_all_repurposed_pieces(client):
    content_id = await _make_content_with_body(client)
    _install_fake_openai_client()
    await client.post(f"/content/{content_id}/repurpose", json={"target_types": ["social_media", "email_copy"]})

    r = await client.get(f"/content/{content_id}/derivatives")

    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    assert {d["content_type"] for d in body["derivatives"]} == {"social_media", "email_copy"}


async def test_list_derivatives_for_nonexistent_content_returns_404(client):
    r = await client.get(f"/content/{uuid.uuid4()}/derivatives")
    assert r.status_code == 404
