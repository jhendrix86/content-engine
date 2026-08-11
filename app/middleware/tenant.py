"""
Tenant middleware for extracting tenant context from requests

This middleware extracts tenant_id from the caller's Unkey API key (this
fleet's real auth mechanism - there is no user login/JWT here, unlike
baselayer) or request headers, and sets it in the tenant context for
database filtering.
"""

from fastapi import Request, HTTPException, status
from uuid import UUID
from loguru import logger
from unkey_auth import get_client, UnkeyError
from app.tenant_context import set_tenant_context, clear_tenant_context


async def tenant_middleware(request: Request, call_next):
    """
    Middleware to extract and set tenant context from requests.

    This middleware attempts to extract tenant_id from:
    1. The caller's Unkey API key - authoritative when present and a
       real UNKEY_ROOT_KEY is configured
    2. X-Tenant-ID header (for testing/internal calls, or as a fallback
       when Method 1 found nothing)

    The tenant context is then available throughout the request lifecycle
    for automatic database query filtering.
    """
    # Try to extract tenant_id from various sources
    tenant_id = None

    # Method 1: From the caller's Unkey key (identity.externalId or
    # meta["tenant_id"] - see unkey-auth's VerifyKeyResult.tenant_id for
    # the exact priority order and this project's key-provisioning
    # convention). This re-verifies the key against Unkey independently
    # of the require_api_key dependency most routers also use for actual
    # auth gating - a deliberate, known double call (tenant extraction
    # happens here, at the ASGI middleware layer, which runs before
    # FastAPI's dependency injection can hand this middleware a
    # dependency's already-computed result) rather than a design flaw.
    # Failures here (no root key configured, key invalid, Unkey
    # unreachable) are swallowed and fall through to X-Tenant-ID -
    # extracting tenant context is not this middleware's job of actually
    # rejecting bad requests, require_api_key still does that separately.
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]  # Remove "Bearer " prefix
        client = get_client()
        if client.config.enabled:
            try:
                result = await client.verify_key(token)
                if result.valid and result.tenant_id:
                    tenant_id = UUID(result.tenant_id)
                    logger.debug(f"Extracted tenant_id from Unkey key: {tenant_id}")
            except UnkeyError as e:
                logger.debug(f"Could not verify Unkey key for tenant extraction: {e}")
            except ValueError:
                logger.warning(f"Unkey key's tenant_id is not a valid UUID: {result.tenant_id}")

    # Method 2: From X-Tenant-ID header (for testing/internal calls,
    # or as a fallback when Method 1 found nothing)
    tenant_id_header = request.headers.get("X-Tenant-ID")
    if tenant_id is None and tenant_id_header:
        try:
            tenant_id = UUID(tenant_id_header)
            logger.debug(f"Extracted tenant_id from X-Tenant-ID header: {tenant_id}")
        except ValueError:
            logger.warning(f"Invalid tenant_id in X-Tenant-ID header: {tenant_id_header}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid tenant_id format in X-Tenant-ID header"
            )
    
    # Set (or explicitly clear) the tenant context for this request.
    # ContextVar state can otherwise leak across requests that share the
    # same context chain (e.g. sequential calls from the same task/
    # connection) if a request without a tenant header simply left a
    # prior request's tenant_id in place instead of clearing it.
    if tenant_id:
        set_tenant_context(tenant_id)
    else:
        clear_tenant_context()

    # Process the request
    response = await call_next(request)

    return response
