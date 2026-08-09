"""
Platform client registry, keyed by the Distribution.platform string.
"""

from .base import PublishResult
from .devto import DevToClient
from .substack import SubstackClient
from .wordpress import WordPressClient

PLATFORM_CLIENTS = {
    "wordpress": WordPressClient,
    "devto": DevToClient,
    "dev.to": DevToClient,
    "substack": SubstackClient,
}


def get_platform_client(platform: str):
    """Return a new client instance for the given platform, or None if unsupported."""
    client_cls = PLATFORM_CLIENTS.get(platform.lower())
    return client_cls() if client_cls else None


__all__ = ["PublishResult", "get_platform_client", "PLATFORM_CLIENTS"]
