"""OCSF audit logging middleware for ThreatRecall API.

Implements OCSF class 6002 (API Activity), 3001 (Authentication), and 3003 (Authorization)
events per GOV-012. This is the centralized audit logging layer.

All API requests are logged as structured OCSF events for SIEM ingestion.
"""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from threatrecall_api.core.ocsf_logger import log_api_activity, log_auth_attempt
from threatrecall_api.core.tenant_storage import tenant_exists


class OCSFAuditMiddleware(BaseHTTPMiddleware):
    """Middleware that logs all API activity as OCSF events."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        start_time = time.perf_counter()

        # Extract tenant_id from path for audit context
        path = str(request.url.path)
        tenant_id = "unknown"

        if path.startswith("/api/v1/"):
            parts = path.split("/")
            if len(parts) >= 4:
                tenant_id = parts[3]
        elif path.startswith("/admin/tenants/"):
            parts = path.split("/")
            if len(parts) >= 4:
                tenant_id = parts[3]

        user_agent = request.headers.get("user-agent")
        src_ip = request.client.host if request.client else None

        try:
            response = await call_next(request)
            process_time = time.perf_counter() - start_time
            latency_ms = process_time * 1000

            # Log as OCSF class 6002 API Activity
            log_api_activity(
                request_id=request_id,
                tenant_id=tenant_id,
                method=request.method,
                path=path,
                status_code=response.status_code,
                latency_ms=latency_ms,
                user_agent=user_agent,
                src_ip=src_ip,
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(round(latency_ms, 2))

            return response

        except Exception as e:
            process_time = time.perf_counter() - start_time
            latency_ms = process_time * 1000

            # Log error as OCSF event
            log_api_activity(
                request_id=request_id,
                tenant_id=tenant_id,
                method=request.method,
                path=path,
                status_code=500,
                latency_ms=latency_ms,
                user_agent=user_agent,
                src_ip=src_ip,
            )

            raise


# Convenience functions for other parts of the application
def log_auth_event(success: bool, tenant_id: str = "unknown", reason: str = None):
    """Log authentication events as OCSF class 3001."""
    log_auth_attempt(
        request_id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        success=success,
        reason=reason
    )
