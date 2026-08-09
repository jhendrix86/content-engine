"""
Substack has no official public API for publishing posts (confirmed by
research, not assumed) - only unofficial, reverse-engineered clients exist,
which are fragile and a Terms of Service risk to build a product feature on.
This client honestly reports that rather than faking success or silently
scraping a private endpoint.
"""

from .base import PublishResult


class SubstackClient:
    configured = False

    async def publish(self, title: str, body: str) -> PublishResult:
        return PublishResult(
            success=False,
            error="Substack has no official public publishing API - not supported",
        )
