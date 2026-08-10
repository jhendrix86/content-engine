"""
Tenant middleware for extracting tenant context from requests

This middleware extracts tenant_id from JWT tokens or request headers
and sets it in the tenant context for database filtering.
"""

from fastapi import Request, HTTPException, status
from uuid import UUID
from loguru import logger
from app.tenant_context import set_tenant_context


async def tenant_middleware(request: Request, call_next):
    """
    Middleware to extract and set tenant context from requests.
    
    This middleware attempts to extract tenant_id from:
    1. Authorization header (JWT token claims)
    2. X-Tenant-ID header (for testing/debugging)
    
    The tenant context is then available throughout the request lifecycle
    for automatic database query filtering.
    """
    # Try to extract tenant_id from various sources
    tenant_id = None
    
    # Method 1: From Authorization header (JWT token)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]  # Remove "Bearer " prefix
        # In production, you'd decode the JWT and extract tenant_id from claims
        # For now, this is a placeholder
        logger.debug("Authorization header present, JWT extraction not yet implemented")
    
    # Method 2: From X-Tenant-ID header (for testing/internal calls)
    tenant_id_header = request.headers.get("X-Tenant-ID")
    if tenant_id_header:
        try:
            tenant_id = UUID(tenant_id_header)
            logger.debug(f"Extracted tenant_id from X-Tenant-ID header: {tenant_id}")
        except ValueError:
            logger.warning(f"Invalid tenant_id in X-Tenant-ID header: {tenant_id_header}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid tenant_id format in X-Tenant-ID header"
            )
    
    # Set the tenant context if found
    if tenant_id:
        set_tenant_context(tenant_id)
    
    # Process the request
    response = await call_next(request)
    
    return response
