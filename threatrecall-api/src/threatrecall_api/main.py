"""FastAPI application entry point.

Per GOV-005: API versioning in URL, standard error handling.
Per GOV-012: OCSF logging, request_id correlation.
"""

import time
import uuid
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from threatrecall_api.api.middleware.rate_limit import RateLimitMiddleware
from threatrecall_api.api.middleware.audit import log_api_activity
from threatrecall_api.api.routes import memory, tenant
from threatrecall_api.core.config import settings
from threatrecall_api.core.logging import configure_logging, get_logger
from threatrecall_api.models.common import ErrorDetail, ErrorResponse

# Configure structured logging on startup
configure_logging(log_level=settings.log_level)
logger = get_logger("threatrecall_api.main")

app = FastAPI(
    title="ThreatRecall API",
    version="1.0.0",
    description="Memory-as-a-Service for Threat Intelligence",
    docs_url="/api/docs",
    redoc_url=None,
)

# Rate limiting middleware
app.add_middleware(RateLimitMiddleware)

app.include_router(tenant.router)
app.include_router(memory.router)


class AuditMiddleware(BaseHTTPMiddleware):
    """Log every API request as OCSF class 6002 per GOV-012."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        start_time = time.perf_counter()

        # Extract tenant_id from path for audit logging
        path = request.url.path
        tenant_id = "unknown"
        if path.startswith("/api/v1/"):
            parts = path.split("/")
            if len(parts) >= 4:
                tenant_id = parts[3]

        src_ip = request.client.host if request.client else None

        try:
            response = await call_next(request)
            process_time = time.perf_counter() - start_time

            response.headers["X-Request-ID"] = request_id

            log_api_activity(
                request_id=request_id,
                tenant_id=tenant_id,
                method=request.method,
                path=path,
                status_code=response.status_code,
                latency_ms=round(process_time * 1000, 2),
                user_agent=request.headers.get("user-agent"),
                src_ip=src_ip,
            )
            return response

        except Exception as e:
            process_time = time.perf_counter() - start_time
            log_api_activity(
                request_id=request_id,
                tenant_id=tenant_id,
                method=request.method,
                path=path,
                status_code=500,
                latency_ms=round(process_time * 1000, 2),
                user_agent=request.headers.get("user-agent"),
                src_ip=src_ip,
            )
            raise


app.add_middleware(AuditMiddleware)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Map FastAPI validation errors to GOV-005 error envelope."""
    details = []
    for error in exc.errors():
        field = ".".join(
            str(loc) for loc in error["loc"] if loc not in ("body", "query", "path")
        )
        details.append(
            ErrorDetail(
                field=field or "request",
                issue=error["type"],
                value=str(error.get("input", "")),
            )
        )

    request_id = request.headers.get("X-Request-ID", "unknown")

    error_response = ErrorResponse(
        code="VALIDATION_ERROR",
        message="Request validation failed",
        details=details,
        request_id=request_id,
        documentation_url="https://docs.threatrecall.com/errors/VALIDATION_ERROR",
    )

    return JSONResponse(
        status_code=400,
        content={"error": error_response.model_dump(exclude_none=True)},
    )


@app.get("/health")
async def root_health():
    """Root health check — no auth required."""
    return {"status": "ok", "service": "threatrecall-api", "version": "1.0.0"}
