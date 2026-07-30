"""
Distribution models
"""

from sqlalchemy import Column, String, Integer, DateTime, Boolean, Enum, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.database import Base


class DistributionStatus(str, enum.Enum):
    """Distribution status enumeration"""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"


class Distribution(Base):
    """Distribution model"""
    __tablename__ = "distributions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_id = Column(UUID(as_uuid=True), ForeignKey("content.id"), nullable=False)
    
    # Distribution details
    platform = Column(String(50), nullable=False)
    platform_post_id = Column(String(255), nullable=True)
    
    # Status
    status = Column(Enum(DistributionStatus), default=DistributionStatus.PENDING)
    
    # Schedule
    scheduled_at = Column(DateTime, nullable=True)
    published_at = Column(DateTime, nullable=True)
    
    # Results
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Metadata
    extra_metadata = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    content = relationship("Content", back_populates="distributions")
    
    def __repr__(self):
        return f"<Distribution {self.id} - {self.platform} - {self.status}>"
