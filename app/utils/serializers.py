"""
Shared helpers for turning SQLAlchemy model instances into JSON-safe dicts.
"""

from datetime import datetime
from enum import Enum
from uuid import UUID
from typing import Any


def _serialize_value(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    return value


def model_to_dict(instance) -> dict:
    """Convert a SQLAlchemy declarative model instance to a JSON-safe dict."""
    return {
        column.name: _serialize_value(getattr(instance, column.name))
        for column in instance.__table__.columns
    }
