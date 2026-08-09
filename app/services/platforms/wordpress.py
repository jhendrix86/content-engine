"""
Real WordPress publishing via the core REST API (POST /wp/v2/posts),
authenticated with an Application Password over HTTP Basic Auth - the
approach WordPress itself documents for self-hosted sites (Users > Profile >
Application Passwords), not a plugin or OAuth flow.

https://developer.wordpress.org/rest-api/reference/posts/#create-a-post
"""

import httpx
from loguru import logger

from app.config import settings
from .base import PublishResult


class WordPressClient:
    def __init__(self):
        self.site_url = settings.wordpress_url.rstrip("/")
        self.username = settings.wordpress_username
        self.app_password = settings.wordpress_app_password

    @property
    def configured(self) -> bool:
        return bool(self.site_url and self.username and self.app_password)

    async def publish(self, title: str, body: str) -> PublishResult:
        if not self.configured:
            return PublishResult(success=False, error="WordPress is not configured (WORDPRESS_URL/WORDPRESS_USERNAME/WORDPRESS_APP_PASSWORD)")

        url = f"{self.site_url}/wp-json/wp/v2/posts"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    url,
                    auth=(self.username, self.app_password),
                    json={"title": title, "content": body, "status": "publish"},
                )
        except httpx.HTTPError as exc:
            logger.error(f"WordPress publish request failed: {exc}")
            return PublishResult(success=False, error=f"WordPress request failed: {exc}")

        if response.status_code not in (200, 201):
            return PublishResult(success=False, error=f"WordPress returned {response.status_code}: {response.text[:300]}")

        data = response.json()
        return PublishResult(success=True, post_id=str(data.get("id")), url=data.get("link"))
