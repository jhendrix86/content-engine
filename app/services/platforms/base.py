"""
Shared result type for platform publishing clients.

Every client returns a PublishResult rather than raising - callers (the
distribution router) always get a clear success/failure to record on the
Distribution row, matching the fleet-wide pattern of honest degradation
over silent mocks or exceptions.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class PublishResult:
    success: bool
    post_id: Optional[str] = None
    url: Optional[str] = None
    error: Optional[str] = None
