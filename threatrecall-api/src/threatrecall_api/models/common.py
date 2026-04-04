"""Shared Pydantic models for API requests and responses.

Per GOV-005: snake_case JSON fields, standard envelope format.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Per GOV-005 error detail format."""

    field: str
    issue: str
    value: str | None = None


class ErrorResponse(BaseModel):
    """Per GOV-005 standard error envelope."""

    code: str
    message: str
    details: list[ErrorDetail] | None = None
    request_id: str
    documentation_url: str | None = None


class ResponseMeta(BaseModel):
    """Per GOV-005 response metadata envelope."""

    request_id: str
    timestamp: datetime


class PaginationMeta(BaseModel):
    """Per GOV-005 cursor-based pagination metadata."""

    cursor: str | None = None
    has_more: bool = False
    page_size: int = 25


class HealthComponents(BaseModel):
    """Component health status for health check endpoint."""

    storage: str = "ok"
    vector_index: str = "ok"
    entity_index: str = "ok"


class HealthMetrics(BaseModel):
    """Operational metrics for health check endpoint."""

    note_count: int = 0
    storage_bytes: int = 0
    last_write: datetime | None = None
