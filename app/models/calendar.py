"""
Calendar models
"""

from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy import Uuid
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base
from app.models.tenant_base import TenantBase


class CalendarEntry(TenantBase, Base):
    """Calendar entry model"""
    __tablename__ = "calendar_entries"
    
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_id = Column(Uuid(as_uuid=True), ForeignKey("content.id"), nullable=True)
    
    # Entry details
    title = Column(String(500), nullable=False)
    description = Column(String(1000), nullable=True)
    
    # Schedule
    scheduled_date = Column(DateTime, nullable=False)
    scheduled_time = Column(String(10), nullable=True)
    
    # Status
    status = Column(String(20), default="scheduled")  # scheduled, published, skipped
    
    # Platforms
    platforms = Column(JSON, nullable=False)  # List of target platforms
    
    # Metadata
    extra_metadata = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    content = relationship("Content")
    
    def __repr__(self):
        return f"<CalendarEntry {self.title} - {self.scheduled_date}>"
