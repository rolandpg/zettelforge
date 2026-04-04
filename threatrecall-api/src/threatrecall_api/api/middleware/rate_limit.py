"""Rate limiting middleware per GOV-005.

In-memory token bucket per tenant (MVP).
Production: replace with Redis-backed sliding window.
"""

import threading
import time
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from threatrecall_api.core.config import settings


class TokenBucket:
    """Thread-safe token bucket for rate limiting."""

    def __init__(self, rate_per_minute: int, rate_per_hour: int) -> None:
        self.rate_per_minute = rate_per_minute
        self.rate_per_hour = rate_per_hour
        self.minute_tokens: float = float(rate_per_minute)
        self.hour_tokens: float = float(rate_per_hour)
        self.last_refill_minute: float = time.time()
        self.last_refill_hour: float = time.time()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        now = time.time()
        elapsed_min = now - self.last_refill_minute
        elapsed_hour = now - self.last_refill_hour

        # Refill minute bucket (tokens per second = rate/60)
        self.minute_tokens = min(
            self.rate_per_minute,
            self.minute_tokens + elapsed_min * (self.rate_per_minute / 60.0),
        )
        self.last_refill_minute = now

        # Refill hour bucket (tokens per second = rate/3600)
        self.hour_tokens = min(
            self.rate_per_hour,
            self.hour_tokens + elapsed_hour * (self.rate_per_hour / 3600.0),
        )
        self.last_refill_hour = now

    def consume(self) -> tuple[bool, int, int]:
        """Attempt to consume one token from both buckets.

        Returns: (allowed, remaining_minute, remaining_hour)
        """
        with self._lock:
            self._refill()
            if self.minute_tokens >= 1.0 and self.hour_tokens >= 1.0:
                self.minute_tokens -= 1.0
                self.hour_tokens -= 1.0
                return True, int(self.minute_tokens), int(self.hour_tokens)
            return False, int(self.minute_tokens), int(self.hour_tokens)


# Global store: tenant_id -> TokenBucket
_rate_limit_store: dict[str, TokenBucket] = {}
_store_lock = threading.Lock()


def get_bucket(tenant_id: str) -> TokenBucket:
    """Get or create a token bucket for a tenant."""
    with _store_lock:
        if tenant_id not in _rate_limit_store:
            _rate_limit_store[tenant_id] = TokenBucket(
                rate_per_minute=settings.rate_limit_requests_per_minute,
                rate_per_hour=settings.rate_limit_requests_per_hour,
            )
        return _rate_limit_store[tenant_id]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limit by tenant_id extracted from path.

    Applies to all /api/v1/{tenant_id}/* routes.
    Skips /admin/* and /docs endpoints.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # Skip rate limiting for admin and docs
        if path.startswith("/admin") or path.startswith("/docs") or path == "/":
            return await call_next(request)

        # Extract tenant_id from /api/v1/{tenant_id}/*
        parts = path.split("/")
        tenant_id: Optional[str] = None
        if len(parts) >= 4 and parts[1] == "api" and parts[2] == "v1":
            tenant_id = parts[3]

        if tenant_id is None:
            return await call_next(request)

        bucket = get_bucket(tenant_id)
        allowed, remaining_min, remaining_hour = bucket.consume()
        reset_min = int(time.time()) + 60
        reset_hour = int(time.time()) + 3600

        response = await call_next(request)

        # Set rate limit headers
        response.headers["X-RateLimit-Limit-Minute"] = str(settings.rate_limit_requests_per_minute)
        response.headers["X-RateLimit-Remaining-Minute"] = str(max(0, remaining_min))
        response.headers["X-RateLimit-Reset-Minute"] = str(reset_min)
        response.headers["X-RateLimit-Limit-Hour"] = str(settings.rate_limit_requests_per_hour)
        response.headers["X-RateLimit-Remaining-Hour"] = str(max(0, remaining_hour))
        response.headers["X-RateLimit-Reset-Hour"] = str(reset_hour)

        if not allowed:
            from fastapi.responses import JSONResponse

            request_id = request.headers.get("X-Request-ID", "unknown")
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMITED",
                        "message": "Rate limit exceeded. Retry after the reset window.",
                        "request_id": request_id,
                        "documentation_url": "https://docs.threatrecall.com/errors/RATE_LIMITED",
                    }
                },
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit-Minute": str(settings.rate_limit_requests_per_minute),
                    "X-RateLimit-Remaining-Minute": "0",
                    "X-RateLimit-Reset-Minute": str(reset_min),
                },
            )

        return response
