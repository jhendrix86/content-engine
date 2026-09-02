"""
Tenant middleware for extracting tenant context from requests

This middleware extracts tenant_id from the caller's Unkey API key (this
fleet's real auth mechanism - there is no user login/JWT here, unlike
baselayer) or request headers, and sets it in the tenant context for
database filtering.

Pure ASGI (not `@app.middleware("http")` / BaseHTTPMiddleware) - deliberate,
not a style choice. BaseHTTPMiddleware's call_next() breaks response body
delivery on error paths when combined with an outer pure-ASGI middleware
that replays a custom `receive` (SafetyBoundaryMiddleware, added after this
one - see empire_operators/middleware.py's own docstring for why it's pure
ASGI). Found 2026-09-01: POST routes returning 422/4xx past this middleware
sent correct headers (Content-Length) but zero body bytes, reproducible
with raw sockets. Converting this middleware to pure ASGI removes the
BaseHTTPMiddleware boundary entirely and fixes it.
"""

from uuid import UUID
import json

from loguru import logger
from unkey_auth import get_client, UnkeyError

from app.tenant_context import set_tenant_context, clear_tenant_context


class TenantMiddleware:
    """
    Extracts and sets tenant context from requests.

    Attempts to extract tenant_id from:
    1. The caller's Unkey API key - authoritative when present and a
       real UNKEY_ROOT_KEY is configured
    2. X-Tenant-ID header (for testing/internal calls, or as a fallback
       when Method 1 found nothing)

    The tenant context is then available throughout the request lifecycle
    for automatic database query filtering.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])}

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
        auth_header = headers.get("authorization")
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
        tenant_id_header = headers.get("x-tenant-id")
        if tenant_id is None and tenant_id_header:
            try:
                tenant_id = UUID(tenant_id_header)
                logger.debug(f"Extracted tenant_id from X-Tenant-ID header: {tenant_id}")
            except ValueError:
                logger.warning(f"Invalid tenant_id in X-Tenant-ID header: {tenant_id_header}")
                await _send_json(send, 400, {"detail": "Invalid tenant_id format in X-Tenant-ID header"})
                return

        # Set (or explicitly clear) the tenant context for this request.
        # ContextVar state can otherwise leak across requests that share the
        # same context chain (e.g. sequential calls from the same task/
        # connection) if a request without a tenant header simply left a
        # prior request's tenant_id in place instead of clearing it.
        if tenant_id:
            set_tenant_context(tenant_id)
        else:
            clear_tenant_context()

        await self.app(scope, receive, send)


async def _send_json(send, status: int, payload: dict):
    body = json.dumps(payload).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("latin-1")),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})
