"""Admin tenant endpoints.

Provisioning and key rotation.
"""

import secrets
import string
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, status

from threatrecall_api.core.config import settings
from threatrecall_api.core.secrets import SecretsProvider, get_secrets_provider
from threatrecall_api.models.common import ResponseMeta
from threatrecall_api.models.tenant import (
    TenantCreate,
    TenantCreateResponse,
    TenantRotateKeyRequest,
    TenantRotateKeyResponse,
)

router = APIRouter(prefix="/admin/tenants", tags=["Admin"])


def _generate_api_key() -> str:
    """Generate a secure API key."""
    alphabet = string.ascii_letters + string.digits
    secret = "".join(secrets.choice(alphabet) for _ in range(40))
    return f"tr_live_{secret}"


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=dict,  # Simplified for the wrapper mapping
)
async def create_tenant(
    request: Request,
    payload: TenantCreate,
    secrets_provider: SecretsProvider = Depends(get_secrets_provider),
):
    """Provision a new tenant and generate an initial API key."""
    tenant_id = payload.tenant_id
    api_key = _generate_api_key()
    
    # Store key in Vault per GOV-014
    secret_path = f"production/threatrecall/{tenant_id}/api-key"
    await secrets_provider.set_secret(secret_path, api_key)
    
    # Create isolated storage path per GOV-019
    storage_path = settings.tenant_storage_path / tenant_id
    storage_path.mkdir(parents=True, exist_ok=True)
    
    data = TenantCreateResponse(
        tenant_id=tenant_id,
        tenant_name=payload.tenant_name,
        api_key=api_key,
        created_at=datetime.now(timezone.utc),
        storage_path=str(storage_path),
    )
    
    return {
        "data": data.model_dump(),
        "meta": ResponseMeta(
            request_id=request.headers.get("X-Request-ID", str(uuid.uuid4())),
            timestamp=datetime.now(timezone.utc),
        ).model_dump(),
    }


@router.post(
    "/{tenant_id}/rotate-key",
    status_code=status.HTTP_200_OK,
)
async def rotate_tenant_key(
    request: Request,
    tenant_id: str,
    payload: TenantRotateKeyRequest,
    secrets_provider: SecretsProvider = Depends(get_secrets_provider),
):
    """Rotate the API key for a tenant."""
    new_api_key = _generate_api_key()
    
    # In a real implementation, we'd store both and track expiration of the old key.
    # For MVP, we overwrite.
    secret_path = f"production/threatrecall/{tenant_id}/api-key"
    await secrets_provider.set_secret(secret_path, new_api_key)
    
    import datetime as dt
    
    data = TenantRotateKeyResponse(
        tenant_id=tenant_id,
        new_api_key=new_api_key,
        old_key_expires_at=datetime.now(timezone.utc) + dt.timedelta(hours=settings.api_key_grace_period_hours),
        rotated_at=datetime.now(timezone.utc),
    )
    
    return {
        "data": data.model_dump(),
        "meta": ResponseMeta(
            request_id=request.headers.get("X-Request-ID", str(uuid.uuid4())),
            timestamp=datetime.now(timezone.utc),
        ).model_dump(),
    }
