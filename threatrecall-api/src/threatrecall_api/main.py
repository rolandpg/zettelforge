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
    docs_url="/api/docs", # Per GOV-005: Swagger at /api/docs
    redoc_url=None,
)

app.include_router(tenant.router)
app.include_router(memory.router)

@app.middleware("http")
async def add_request_id_and_log(request: Request, call_next: Callable) -> Response:
    """Middleware to ensure request_id exists and log the request per GOV-012."""
    # Use client provided ID if available, otherwise generate UUIDv4
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    
    # Bind request_id to logger context for this request
    start_time = time.perf_counter()
    
    try:
        response = await call_next(request)
        process_time = time.perf_counter() - start_time
        
        # Add tracking headers
        response.headers["X-Request-ID"] = request_id
        
        # Rate limit headers per GOV-005 (Mocked for MVP structure)
        response.headers["X-RateLimit-Limit"] = str(settings.rate_limit_requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(settings.rate_limit_requests_per_minute - 1)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 60)
        
        logger.info(
            "api_request",
            class_uid=6002,
            class_name="API Activity",
            category_uid=3,
            activity_id=1,
            status_id=1,
            request_id=request_id,
            http_request={
                "method": request.method,
                "url": str(request.url.path),
                "user_agent": request.headers.get("user-agent"),
            },
            http_response={
                "code": response.status_code,
                "latency_ms": round(process_time * 1000, 2),
            },
        )
        return response
        
    except Exception as e:
        # Log unhandled exceptions
        logger.error(
            "internal_server_error",
            class_uid=6002,
            class_name="API Activity",
            status_id=2,
            request_id=request_id,
            error=str(e),
            exc_info=True,
        )
        raise

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Map FastAPI validation errors to GOV-005 error envelope."""
    details = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"] if loc not in ("body", "query", "path"))
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
