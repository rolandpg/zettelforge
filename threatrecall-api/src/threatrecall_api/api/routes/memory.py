"""Memory-as-a-Service endpoints.

Remember, recall, and manage notes.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Request, status

from threatrecall_api.api.dependencies import TenantContext
from threatrecall_api.models.common import HealthComponents, HealthMetrics, HealthResponse, ResponseMeta
from threatrecall_api.models.note import (
    RecallRequest,
    RememberRequest,
    RememberResponse,
)

router = APIRouter(prefix="/api/v1", tags=["Memory"])


@router.get("/{tenant_id}/health", status_code=status.HTTP_200_OK)
async def tenant_health(request: Request, tenant_id: TenantContext):
    """Health check for isolated tenant resources."""
    
    data = HealthResponse(
        tenant_id=tenant_id,
        components=HealthComponents().model_dump(),
        metrics=HealthMetrics(note_count=0, storage_bytes=0).model_dump(),
    )
    
    return {
        "data": data.model_dump(),
        "meta": ResponseMeta(
            request_id=request.headers.get("X-Request-ID", str(uuid.uuid4())),
            timestamp=datetime.now(timezone.utc),
        ).model_dump(),
    }


@router.post("/{tenant_id}/remember", status_code=status.HTTP_201_CREATED)
async def remember(request: Request, tenant_id: TenantContext, payload: RememberRequest):
    """Store a note in memory."""
    
    # MOCK implementation connecting to backend logic later
    note_id = f"note-{uuid.uuid4().hex[:8]}"
    
    data = RememberResponse(
        note_id=note_id,
        content=payload.content,
        created_at=datetime.now(timezone.utc),
        entities=[],
        linked_notes=[],
    )
    
    return {
        "data": data.model_dump(),
        "meta": ResponseMeta(
            request_id=request.headers.get("X-Request-ID", str(uuid.uuid4())),
            timestamp=datetime.now(timezone.utc),
        ).model_dump(),
    }


@router.post("/{tenant_id}/recall", status_code=status.HTTP_200_OK)
async def recall(request: Request, tenant_id: TenantContext, payload: RecallRequest):
    """Semantic search across stored notes."""
    
    # MOCK implementation
    
    return {
        "data": [],
        "meta": ResponseMeta(
            request_id=request.headers.get("X-Request-ID", str(uuid.uuid4())),
            timestamp=datetime.now(timezone.utc),
        ).model_dump(),
        "pagination": {
            "cursor": None,
            "has_more": False,
            "page_size": payload.options.limit if payload.options else 10,
        }
    }
