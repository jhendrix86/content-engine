"""
Configuration management for Content Engine
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # Database
    database_url: str = os.getenv("DATABASE_URL", "postgresql://localhost/content")
    
    # Redis
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # AI
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    ai_model: str = os.getenv("AI_MODEL", "gpt-4")

    # Platform publishing
    wordpress_url: str = os.getenv("WORDPRESS_URL", "")
    wordpress_username: str = os.getenv("WORDPRESS_USERNAME", "")
    wordpress_app_password: str = os.getenv("WORDPRESS_APP_PASSWORD", "")
    devto_api_key: str = os.getenv("DEVTO_API_KEY", "")

    # Application
    app_name: str = "Content Engine"
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Integration
    marketing_automation_url: str = os.getenv("MARKETING_AUTOMATION_URL", "http://localhost:8039")
    analytics_engine_url: str = os.getenv("ANALYTICS_ENGINE_URL", "http://localhost:8042")
    funnel_automation_url: str = os.getenv("FUNNEL_AUTOMATION_URL", "http://localhost:8000")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # tolerate env vars owned by other libs (e.g. unkey-auth's UNKEY_*)


settings = Settings()
