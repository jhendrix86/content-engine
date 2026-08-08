"""
Confirms the Unkey pilot wiring on this engine: fails open (no auth required)
when UNKEY_ROOT_KEY isn't configured, and actually enforces once it is.
"""
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
    yield


@pytest.mark.asyncio
async def test_routes_work_without_auth_header_when_unkey_not_configured(client, monkeypatch):
    monkeypatch.delenv("UNKEY_ROOT_KEY", raising=False)

    response = await client.get("/content/")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_missing_key_rejected_once_unkey_is_configured(client, monkeypatch):
    monkeypatch.setattr(
        unkey_middleware,
        "_client",
        UnkeyClient(Config(unkey_root_key="root_test", unkey_base_url="https://api.unkey.com/v2")),
    )

    response = await client.get("/content/")

    assert response.status_code == 401


@pytest.mark.asyncio
@respx.mock
async def test_valid_key_passes_through_once_unkey_is_configured(client, monkeypatch):
    monkeypatch.setattr(
        unkey_middleware,
        "_client",
        UnkeyClient(Config(unkey_root_key="root_test", unkey_base_url="https://api.unkey.com/v2")),
    )
    respx.post("https://api.unkey.com/v2/keys.verifyKey").mock(
        return_value=httpx.Response(200, json={"meta": {}, "data": {"valid": True, "code": "VALID"}})
    )

    response = await client.get("/content/", headers={"Authorization": "Bearer unkey_live_test"})

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_check_never_requires_auth(client, monkeypatch):
    monkeypatch.setattr(
        unkey_middleware,
        "_client",
        UnkeyClient(Config(unkey_root_key="root_test", unkey_base_url="https://api.unkey.com/v2")),
    )

    response = await client.get("/health")

    assert response.status_code == 200
