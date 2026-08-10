"""
Tenant base mixin for multi-tenancy support

This mixin provides tenant_id field for all models that need tenant isolation.
"""

from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid


class TenantBase:
    """
    Mixin class that adds tenant_id to models for multi-tenancy.
    
    All models that require tenant isolation should inherit from this mixin
    along with their regular base class.
    """
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant identifier for data isolation"
    )
