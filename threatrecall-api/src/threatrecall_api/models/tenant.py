"""Tenant management models."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from threatrecall_api.models.common import ResponseMeta


class TenantCreate(BaseModel):
    """Request to create a new tenant."""

    tenant_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        pattern=r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$",
        description="Lowercase alphanumeric with hyphens, max 64 chars",
    )
    tenant_name: str = Field(..., min_length=1, max_length=255)
    contact_email: EmailStr


class TenantCreateResponse(BaseModel):
    """Response after tenant creation."""

    tenant_id: str
    tenant_name: str
    api_key: str
    created_at: datetime
    storage_path: str


class TenantRotateKeyRequest(BaseModel):
    """Request to rotate tenant API key."""

    reason: str = Field(default="scheduled_rotation")


class TenantRotateKeyResponse(BaseModel):
    """Response after API key rotation."""

    tenant_id: str
    new_api_key: str
    old_key_expires_at: datetime
    rotated_at: datetime


class TenantDeleteResponse(BaseModel):
    """Response for tenant deletion (soft delete)."""

    tenant_id: str
    status: str = "scheduled_deletion"
    deletion_at: datetime
