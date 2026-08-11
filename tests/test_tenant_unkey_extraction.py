"""
Verifies tenant_middleware's Method 1 (extracting tenant_id from the
caller's Unkey key) actually works end-to-end - not just that it fails
open safely when Unkey isn't configured (test_unkey_auth.py already
covers that). Uses the same singleton-injection + respx-mocking pattern
as test_unkey_auth.py.
"""

import uuid

import httpx
import pytest
import respx
from unkey_auth import middleware as unkey_middleware
from unkey_auth.client import UnkeyClient
from unkey_auth.config import Config


@pytest.fixture(autouse=True)
def reset_unkey_singleton(monkeypatch):
    monkeypatch.setattr(unkey_middleware, "_client", None)
    monkeypatch.setattr(unkey_middleware, "_warned_disabled", False)
    monkeypatch.setattr(
        unkey_middleware,
        "_client",
        UnkeyClient(Config(unkey_root_key="root_test", unkey_base_url="https://api.unkey.com/v2")),
    )
    yield


def _mock_verify(key_to_tenant: dict):
    """Each key in key_to_tenant verifies as valid, carrying its mapped tenant_id as identity.externalId."""
    def side_effect(request: httpx.Request) -> httpx.Response:
        import json

        body = json.loads(request.content)
        key = body.get("key")
        tenant_id = key_to_tenant.get(key)
        if tenant_id is None:
            return httpx.Response(200, json={"meta": {}, "data": {"valid": False, "code": "NOT_FOUND"}})
        return httpx.Response(
            200,
            json={
                "meta": {},
                "data": {
                    "valid": True, "code": "VALID", "keyId": f"key_{key}",
                    "identity": {"id": "id_1", "externalId": tenant_id, "meta": {}},
                },
            },
        )

    respx.post("https://api.unkey.com/v2/keys.verifyKey").mock(side_effect=side_effect)


@pytest.mark.asyncio
@respx.mock
async def test_bearer_key_with_identity_sets_tenant_context_and_scopes_content(client):
    tenant_a = str(uuid.uuid4())
    tenant_b = str(uuid.uuid4())
    _mock_verify({"key_for_tenant_a": tenant_a, "key_for_tenant_b": tenant_b})

    created = await client.post(
        "/content/generate",
        json={"title": "A's article", "content_type": "blog_post", "topic": "widgets"},
        headers={"Authorization": "Bearer key_for_tenant_a"},
    )
    assert created.status_code == 200
    content_id = created.json()["id"]

    same_tenant = await client.get(
        f"/content/{content_id}", headers={"Authorization": "Bearer key_for_tenant_a"}
    )
    assert same_tenant.status_code == 200

    # A different, otherwise-valid key belonging to a different Unkey
    # identity should not see it.
    other_tenant = await client.get(
        f"/content/{content_id}", headers={"Authorization": "Bearer key_for_tenant_b"}
    )
    assert other_tenant.status_code == 404


@pytest.mark.asyncio
@respx.mock
async def test_bearer_key_without_identity_falls_back_to_x_tenant_id(client):
    """A valid key with no Identity/meta set carries no tenant_id - X-Tenant-ID still works as a fallback."""
    respx.post("https://api.unkey.com/v2/keys.verifyKey").mock(
        return_value=httpx.Response(200, json={"meta": {}, "data": {"valid": True, "code": "VALID"}})
    )
    tenant_id = str(uuid.uuid4())

    created = await client.post(
        "/content/generate",
        json={"title": "Fallback article", "content_type": "blog_post", "topic": "widgets"},
        headers={"Authorization": "Bearer some_valid_key", "X-Tenant-ID": tenant_id},
    )
    assert created.status_code == 200

    listing = await client.get(
        "/content/", headers={"Authorization": "Bearer some_valid_key", "X-Tenant-ID": tenant_id}
    )
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
