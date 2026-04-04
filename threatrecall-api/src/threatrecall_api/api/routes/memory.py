"""Memory-as-a-Service endpoints.

Remember, recall, and manage notes.
Per GOV-005: standard envelope, cursor pagination, error codes.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, status

from threatrecall_api.api.dependencies import TenantContext
from threatrecall_api.api.middleware.audit import log_auth_attempt
from threatrecall_api.core.tenant_storage import get_memory_manager, tenant_exists
from threatrecall_api.models.common import (
    PaginationMeta,
    ResponseMeta,
)
from threatrecall_api.models.note import (
    RecallOptions,
    RecallRequest,
    RecallResultNote,
    RememberRequest,
    RememberResponse,
    NoteDetail,
    HealthComponents,
    HealthMetrics,
    HealthResponse,
)

router = APIRouter(prefix="/api/v1", tags=["Memory"])


@router.get("/{tenant_id}/health", status_code=status.HTTP_200_OK)
async def tenant_health(request: Request, tenant_id: str):
    """Health check for isolated tenant resources. No auth required."""
    if not tenant_exists(tenant_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RESOURCE_NOT_FOUND", "message": f"Tenant {tenant_id} not found"},
        )

    try:
        mm = get_memory_manager(tenant_id)
        note_count = mm.stats.get("notes_created", 0)

        # Get storage size
        from threatrecall_api.core.tenant_storage import get_tenant_storage_path
        tenant_path = get_tenant_storage_path(tenant_id)
        notes_file = tenant_path / "notes.jsonl"
        storage_bytes = notes_file.stat().st_size if notes_file.exists() else 0

        data = HealthResponse(
            tenant_id=tenant_id,
            status="healthy",
            components=HealthComponents().model_dump(),
            metrics=HealthMetrics(
                note_count=note_count,
                storage_bytes=storage_bytes,
            ).model_dump(),
        )
    except Exception as e:
        data = HealthResponse(
            tenant_id=tenant_id,
            status="degraded",
            components=HealthComponents(storage="error").model_dump(),
            metrics={},
        )

    return {
        "data": data.model_dump(),
        "meta": ResponseMeta(
            request_id=request.headers.get("X-Request-ID", str(uuid.uuid4())),
            timestamp=datetime.now(timezone.utc),
        ).model_dump(),
    }


@router.post("/{tenant_id}/remember", status_code=status.HTTP_201_CREATED)
async def remember(
    request: Request,
    tenant_id: TenantContext,
    payload: RememberRequest,
) -> dict:
    """Store a note in memory with entity extraction and linking.

    Runs the full MemoryManager pipeline: deduplication → enrichment →
    entity indexing → link generation → evolution.
    """
    mm = get_memory_manager(tenant_id)

    # Map request to MemoryManager signature
    source_type = "ingestion"
    if payload.metadata and payload.metadata.source:
        if "cisa" in payload.metadata.source.lower():
            source_type = "authoritative"
        elif "operator" in payload.metadata.source.lower():
            source_type = "conversation"

    try:
        note, reason = mm.remember(
            content=payload.content,
            source_type=source_type,
            source_ref=payload.metadata.source if payload.metadata else "",
            domain="security_ops",
            auto_evolve=payload.options.extract_entities
            if payload.options
            else True,
        )

        if note is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "CONFLICT",
                    "message": f"Duplicate note skipped: {reason}",
                },
            )

        entities_out = []
        if payload.options and payload.options.extract_entities:
            for ent in note.semantic.entities or []:
                entities_out.append(
                    {"type": "entity", "name": ent, "confidence": 0.9}
                )

        response_note = RememberResponse(
            note_id=note.id,
            content=note.content.raw,
            created_at=datetime.fromisoformat(note.created_at),
            entities=entities_out,
            linked_notes=note.links.related if note.links else [],
        )

        return {
            "data": response_note.model_dump(),
            "meta": ResponseMeta(
                request_id=request.headers.get("X-Request-ID", str(uuid.uuid4())),
                timestamp=datetime.now(timezone.utc),
            ).model_dump(),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "INTERNAL_ERROR",
                "message": str(e),
            },
        ) from e


@router.post("/{tenant_id}/recall", status_code=status.HTTP_200_OK)
async def recall(
    request: Request,
    tenant_id: TenantContext,
    payload: RecallRequest,
) -> dict:
    """Semantic search across stored notes using vector retrieval."""
    mm = get_memory_manager(tenant_id)

    limit = 10
    if payload.options:
        limit = payload.options.limit

    try:
        notes = mm.recall(
            query=payload.query,
            k=limit,
            include_links=payload.options.include_entities
            if payload.options
            else True,
        )

        results = []
        for note in notes:
            # Calculate a synthetic relevance score from metadata
            score = note.metadata.confidence if note.metadata else 0.5
            results.append(
                RecallResultNote(
                    note_id=note.id,
                    content=note.content.raw,
                    score=score,
                    created_at=datetime.fromisoformat(note.created_at),
                    entities=[
                        {"type": "entity", "name": e, "confidence": 0.9}
                        for e in (note.semantic.entities or [])
                    ],
                )
            )

        return {
            "data": [r.model_dump() for r in results],
            "meta": ResponseMeta(
                request_id=request.headers.get("X-Request-ID", str(uuid.uuid4())),
                timestamp=datetime.now(timezone.utc),
            ).model_dump(),
            "pagination": PaginationMeta(
                has_more=len(results) == limit,
                page_size=limit,
            ).model_dump(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "INTERNAL_ERROR",
                "message": str(e),
            },
        ) from e
