"""Memory/note models for remember and recall endpoints."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TLPC classification(str, Enum):
    """TLP classifications per GOV-021 DATA-CLASSIFICATION-POLICY."""

    TLP_WHITE = "TLP_WHITE"
    TLP_GREEN = "TLP_GREEN"
    TLP_AMBER = "TLP_AMBER"
    TLP_AMBER_RED = "TLP_AMBER_RED"
    TLP_RED = "TLP_RED"


class NoteMetadata(BaseModel):
    """Optional metadata for a note."""

    source: str | None = None
    confidence: str | None = None
    tlp: TLPC classification | None = None


class EntityInfo(BaseModel):
    """Extracted entity from note content."""

    type: str  # threat_actor, cve, ioc_ipv4, etc.
    name: str
    confidence: float = Field(..., ge=0.0, le=1.0)


class NoteOptions(BaseModel):
    """Options for remember endpoint processing."""

    extract_entities: bool = True
    link_existing: bool = True


class RememberRequest(BaseModel):
    """Request to store a new note."""

    content: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Note content, max 10000 characters",
    )
    metadata: NoteMetadata | None = None
    options: NoteOptions | None = None


class RememberResponse(BaseModel):
    """Response after storing a note."""

    note_id: str
    content: str
    created_at: datetime
    entities: list[EntityInfo] = []
    linked_notes: list[str] = []


class RecallOptions(BaseModel):
    """Options for recall query."""

    limit: int = Field(default=10, ge=1, le=100)
    include_entities: bool = True
    min_confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    filters: dict[str, Any] | None = None


class RecallRequest(BaseModel):
    """Semantic search request."""

    query: str = Field(..., min_length=1, max_length=1000)
    options: RecallOptions | None = None


class RecallResultNote(BaseModel):
    """Single note result from recall."""

    note_id: str
    content: str
    score: float = Field(..., ge=0.0, le=1.0)
    created_at: datetime
    entities: list[EntityInfo] = []


class NoteDetail(BaseModel):
    """Full note detail for GET /notes/{note_id}."""

    note_id: str
    content: str
    created_at: datetime
    updated_at: datetime
    metadata: NoteMetadata | None = None
    entities: list[EntityInfo] = []
    links: list[dict[str, str]] = []


class HealthResponse(BaseModel):
    """Tenant health check response."""

    tenant_id: str
    status: str = "healthy"
    components: dict[str, str]
    metrics: dict[str, Any]
