"""
Verifies the automatic tenant query filtering added to app/database.py
actually isolates data between tenants, not just that it no-ops safely
when no tenant context is set (the rest of the suite already covers that
implicitly - every other test runs with no X-Tenant-ID header at all).
"""

import uuid

TENANT_A = str(uuid.uuid4())
TENANT_B = str(uuid.uuid4())


async def _create_content(client, tenant_id, title):
    resp = await client.post(
        "/content/generate",
        json={"title": title, "content_type": "blog_post", "topic": "widgets"},
        headers={"X-Tenant-ID": tenant_id},
    )
    assert resp.status_code == 200
    return resp.json()["id"]


async def test_tenant_cannot_read_another_tenants_content(client):
    content_id = await _create_content(client, TENANT_A, "Tenant A's article")

    same_tenant = await client.get(f"/content/{content_id}", headers={"X-Tenant-ID": TENANT_A})
    assert same_tenant.status_code == 200

    other_tenant = await client.get(f"/content/{content_id}", headers={"X-Tenant-ID": TENANT_B})
    assert other_tenant.status_code == 404


async def test_list_content_is_scoped_per_tenant(client):
    await _create_content(client, TENANT_A, "A's first post")
    await _create_content(client, TENANT_A, "A's second post")
    await _create_content(client, TENANT_B, "B's only post")

    a_listing = await client.get("/content/", headers={"X-Tenant-ID": TENANT_A})
    assert a_listing.status_code == 200
    assert a_listing.json()["total"] == 2

    b_listing = await client.get("/content/", headers={"X-Tenant-ID": TENANT_B})
    assert b_listing.status_code == 200
    assert b_listing.json()["total"] == 1


async def test_no_tenant_header_sees_everything(client):
    """Fail-open posture: no X-Tenant-ID means no filtering is applied."""
    await _create_content(client, TENANT_A, "A's post")
    await _create_content(client, TENANT_B, "B's post")

    unscoped = await client.get("/content/")
    assert unscoped.status_code == 200
    assert unscoped.json()["total"] == 2
