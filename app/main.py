"""
Content Engine - Main Application
AI-powered content generation and management system for the Autonomous Company OS
"""

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger
import os

from datetime import datetime

from unkey_auth import require_api_key

from app.config import settings
from app.database import init_db
from app.services.ai_writer import AIWriter
from app.routers import content, seo, calendar, distribution, analytics
from app.middleware.tenant import TenantMiddleware
from empire_operators.middleware import SafetyBoundaryMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting Content Engine...")

    # Initialize database
    await init_db()

    # Single shared AI writer instance for the app's lifetime
    app.state.ai_writer = AIWriter()

    logger.info("Content Engine started successfully")
    yield

    logger.info("Shutting down Content Engine...")


# Create FastAPI application
app = FastAPI(
    title="Content Engine",
    description="AI-powered content generation and management system for the Autonomous Company OS",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS — see SECURITY_REVIEW.md finding #1: no wildcard with
# credentials; allowed origins come from the ALLOWED_ORIGINS env var.
def _cors_allowed_origins() -> list:
    # SECURITY_REVIEW.md #1 — no wildcard with credentials. Set
    # ALLOWED_ORIGINS (comma-separated) when a browser client exists.
    import os
    return [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add tenant middleware for multi-tenancy support
app.add_middleware(TenantMiddleware)

# Reject request bodies matching known-unsafe patterns (prompt injection,
# `drop table`, `<script>`) before they reach a router. empire_os
# SafetyBoundaryOperator — first Phase B wire, see
# empire_os/EMPIRE_OS_INTEGRATION_ANALYSIS.md + SECURITY_REVIEW.md.
app.add_middleware(SafetyBoundaryMiddleware)

# Include routers - gated by Unkey key verification (fails open until
# UNKEY_ROOT_KEY is configured; see unkey-auth/README.md)
_auth = [Depends(require_api_key)]
app.include_router(content.router, prefix="/content", tags=["content"], dependencies=_auth)
app.include_router(seo.router, prefix="/seo", tags=["seo"], dependencies=_auth)
app.include_router(calendar.router, prefix="/calendar", tags=["calendar"], dependencies=_auth)
app.include_router(distribution.router, prefix="/distribution", tags=["distribution"], dependencies=_auth)
app.include_router(analytics.router, prefix="/analytics", tags=["analytics"], dependencies=_auth)


@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "Content Engine",
        "version": "1.0.0",
        "status": "operational",
        "description": "AI-powered content generation and management system",
        "features": [
            "AI content generation",
            "SEO optimization",
            "Multi-platform distribution",
            "Content calendar",
            "Performance tracking",
            "Content repurposing",
            "A/B testing",
            "Analytics dashboard"
        ],
        "endpoints": {
            "content": "/content",
            "seo": "/seo",
            "calendar": "/calendar",
            "distribution": "/distribution",
            "analytics": "/analytics"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    logger.info("Health check performed")
    return {
        "status": "healthy",
        "service": "content-engine",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8040,
        reload=True
    )
