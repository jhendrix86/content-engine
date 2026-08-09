"""
Content models
"""

from sqlalchemy import Column, String, Integer, DateTime, Boolean, Enum, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.database import Base


class ContentType(str, enum.Enum):
    """Content type enumeration"""
    BLOG_POST = "blog_post"
    SOCIAL_MEDIA = "social_media"
    EMAIL_COPY = "email_copy"
    LANDING_PAGE = "landing_page"
    VIDEO_SCRIPT = "video_script"
    PRODUCT_DESCRIPTION = "product_description"


class ContentStatus(str, enum.Enum):
    """Content status enumeration"""
    DRAFT = "draft"
    GENERATING = "generating"
    READY = "ready"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class Content(Base):
    """Content model"""
    __tablename__ = "content"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Content details
    title = Column(String(500), nullable=False)
    content_type = Column(Enum(ContentType), nullable=False)
    status = Column(Enum(ContentStatus), default=ContentStatus.DRAFT)
    
    # Content
    body = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)

    # Repurposing: set when this piece was generated FROM another piece
    # (the "pillar"), rather than from a topic directly.
    source_content_id = Column(UUID(as_uuid=True), ForeignKey("content.id"), nullable=True)

    # Generation metadata
    topic = Column(String(500), nullable=True)
    target_audience = Column(String(255), nullable=True)
    tone = Column(String(50), nullable=True)
    length = Column(Integer, nullable=True)
    
    # AI generation
    ai_model = Column(String(50), nullable=True)
    generation_prompt = Column(Text, nullable=True)
    
    # SEO
    seo_score = Column(Integer, nullable=True)
    keywords = Column(JSON, nullable=True)
    
    # Performance
    views = Column(Integer, default=0)
    engagements = Column(Integer, default=0)
    conversions = Column(Integer, default=0)
    
    # Metadata
    extra_metadata = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    published_at = Column(DateTime, nullable=True)
    
    # Relationships
    seo_analysis = relationship("SEOAnalysis", back_populates="content")
    distributions = relationship("Distribution", back_populates="content")
    source_content = relationship("Content", remote_side=[id], back_populates="derivatives")
    derivatives = relationship("Content", back_populates="source_content")
    
    def __repr__(self):
        return f"<Content {self.id} - {self.title} - {self.status}>"
