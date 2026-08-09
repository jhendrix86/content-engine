"""
Real dev.to publishing via the Forem API (POST https://dev.to/api/articles),
authenticated with an api-key header.

https://developers.forem.com/api/v1#tag/articles/operation/createArticle
"""

from typing import List, Optional

import httpx
from loguru import logger

from app.config import settings
from .base import PublishResult

_API_URL = "https://dev.to/api/articles"


class DevToClient:
    def __init__(self):
        self.api_key = settings.devto_api_key

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    async def publish(self, title: str, body: str, tags: Optional[List[str]] = None) -> PublishResult:
        if not self.configured:
            return PublishResult(success=False, error="dev.to is not configured (DEVTO_API_KEY)")

        payload = {
            "article": {
                "title": title,
                "body_markdown": body,
                "published": True,
                # dev.to allows at most 4 tags
                "tags": ",".join((tags or [])[:4]),
            }
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    _API_URL,
                    headers={"api-key": self.api_key, "Content-Type": "application/json"},
                    json=payload,
                )
        except httpx.HTTPError as exc:
            logger.error(f"dev.to publish request failed: {exc}")
            return PublishResult(success=False, error=f"dev.to request failed: {exc}")

        if response.status_code != 201:
            return PublishResult(success=False, error=f"dev.to returned {response.status_code}: {response.text[:300]}")

        data = response.json()
        return PublishResult(success=True, post_id=str(data.get("id")), url=data.get("url"))
