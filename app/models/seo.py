"""
SEO models
"""

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base
from app.models.tenant_base import TenantBase


class SEOAnalysis(TenantBase, Base):
    """SEO analysis model"""
    __tablename__ = "seo_analyses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_id = Column(UUID(as_uuid=True), ForeignKey("content.id"), nullable=False)
    
    # SEO scores
    overall_score = Column(Integer, nullable=True)
    readability_score = Column(Integer, nullable=True)
    keyword_density_score = Column(Integer, nullable=True)
    structure_score = Column(Integer, nullable=True)
    
    # Meta tags
    meta_title = Column(String(500), nullable=True)
    meta_description = Column(Text, nullable=True)
    
    # Keywords
    primary_keyword = Column(String(255), nullable=True)
    secondary_keywords = Column(JSON, nullable=True)
    
    # Recommendations
    recommendations = Column(JSON, nullable=True)
    
    # Timestamps
    analyzed_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    content = relationship("Content", back_populates="seo_analysis")
    
    def __repr__(self):
        return f"<SEOAnalysis {self.content_id} - {self.overall_score}>"


class Keyword(TenantBase, Base):
    """Keyword model"""
    __tablename__ = "keywords"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_id = Column(UUID(as_uuid=True), ForeignKey("content.id"), nullable=True)
    
    # Keyword details
    keyword = Column(String(255), nullable=False)
    search_volume = Column(Integer, nullable=True)
    difficulty = Column(Integer, nullable=True)
    relevance = Column(Integer, nullable=True)
    
    # Position
    current_position = Column(Integer, nullable=True)
    target_position = Column(Integer, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<Keyword {self.keyword} - {self.relevance}>"
