import httpx
import pytest
import respx

from app.services.platforms import get_platform_client
from app.services.platforms.devto import DevToClient
from app.services.platforms.substack import SubstackClient
from app.services.platforms.wordpress import WordPressClient


class TestGetPlatformClient:
    def test_returns_wordpress_client(self):
        assert isinstance(get_platform_client("wordpress"), WordPressClient)

    def test_returns_devto_client_for_either_alias(self):
        assert isinstance(get_platform_client("devto"), DevToClient)
        assert isinstance(get_platform_client("dev.to"), DevToClient)

    def test_returns_substack_client(self):
        assert isinstance(get_platform_client("substack"), SubstackClient)

    def test_is_case_insensitive(self):
        assert isinstance(get_platform_client("WordPress"), WordPressClient)

    def test_returns_none_for_unknown_platform(self):
        assert get_platform_client("myspace") is None


class TestWordPressClient:
    @pytest.mark.asyncio
    async def test_reports_honest_failure_when_not_configured(self, monkeypatch):
        import app.config as config_module
        monkeypatch.setattr(config_module.settings, "wordpress_url", "")
        client = WordPressClient()

        result = await client.publish("Title", "Body")

        assert result.success is False
        assert "not configured" in result.error

    @pytest.mark.asyncio
    @respx.mock
    async def test_publishes_and_parses_id_and_link(self, monkeypatch):
        import app.config as config_module
        monkeypatch.setattr(config_module.settings, "wordpress_url", "https://example.com")
        monkeypatch.setattr(config_module.settings, "wordpress_username", "admin")
        monkeypatch.setattr(config_module.settings, "wordpress_app_password", "app-pass")

        respx.post("https://example.com/wp-json/wp/v2/posts").mock(
            return_value=httpx.Response(201, json={"id": 42, "link": "https://example.com/?p=42"})
        )

        client = WordPressClient()
        result = await client.publish("My Title", "My Body")

        assert result.success is True
        assert result.post_id == "42"
        assert result.url == "https://example.com/?p=42"

    @pytest.mark.asyncio
    @respx.mock
    async def test_reports_honest_failure_on_error_status(self, monkeypatch):
        import app.config as config_module
        monkeypatch.setattr(config_module.settings, "wordpress_url", "https://example.com")
        monkeypatch.setattr(config_module.settings, "wordpress_username", "admin")
        monkeypatch.setattr(config_module.settings, "wordpress_app_password", "wrong-pass")

        respx.post("https://example.com/wp-json/wp/v2/posts").mock(
            return_value=httpx.Response(401, json={"code": "rest_forbidden"})
        )

        client = WordPressClient()
        result = await client.publish("My Title", "My Body")

        assert result.success is False
        assert "401" in result.error


class TestDevToClient:
    @pytest.mark.asyncio
    async def test_reports_honest_failure_when_not_configured(self, monkeypatch):
        import app.config as config_module
        monkeypatch.setattr(config_module.settings, "devto_api_key", "")
        client = DevToClient()

        result = await client.publish("Title", "Body")

        assert result.success is False
        assert "not configured" in result.error

    @pytest.mark.asyncio
    @respx.mock
    async def test_publishes_and_parses_id_and_url(self, monkeypatch):
        import app.config as config_module
        monkeypatch.setattr(config_module.settings, "devto_api_key", "devto-key")

        route = respx.post("https://dev.to/api/articles").mock(
            return_value=httpx.Response(201, json={"id": 99, "url": "https://dev.to/user/my-title-abc"})
        )

        client = DevToClient()
        result = await client.publish("My Title", "My Body", tags=["ai", "python", "webdev", "testing", "extra"])

        assert result.success is True
        assert result.post_id == "99"
        assert result.url == "https://dev.to/user/my-title-abc"

        sent = route.calls.last.request
        import json
        body = json.loads(sent.content)
        assert body["article"]["tags"] == "ai,python,webdev,testing"  # capped at 4
        assert sent.headers["api-key"] == "devto-key"

    @pytest.mark.asyncio
    @respx.mock
    async def test_reports_honest_failure_on_error_status(self, monkeypatch):
        import app.config as config_module
        monkeypatch.setattr(config_module.settings, "devto_api_key", "devto-key")

        respx.post("https://dev.to/api/articles").mock(
            return_value=httpx.Response(422, json={"error": "title is too short"})
        )

        client = DevToClient()
        result = await client.publish("hi", "Body")

        assert result.success is False
        assert "422" in result.error


class TestSubstackClient:
    @pytest.mark.asyncio
    async def test_always_reports_unsupported(self):
        client = SubstackClient()

        result = await client.publish("Title", "Body")

        assert result.success is False
        assert "no official public publishing API" in result.error
