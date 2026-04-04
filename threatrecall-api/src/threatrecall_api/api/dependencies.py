"""FastAPI dependencies per GOV-005 and GOV-014.

Authentication, rate limiting, and tenant context injection.
"""

import secrets
from typing import Annotated

from fastapi import Depends, HTTPException, Path, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from threatrecall_api.core.secrets import get_secrets_provider, SecretsProvider

# Per GOV-005: Bearer token authentication
security = HTTPBearer()

async def get_tenant_api_key(
    tenant_id: str,
    secrets_provider: SecretsProvider = Depends(get_secrets_provider),
) -> str:
    """Retrieve the expected API key for a tenant from the secrets store.
    
    Path convention: production/threatrecall/{tenant_id}/api-key
    """
    secret_path = f"production/threatrecall/{tenant_id}/api-key"
    try:
        return await secrets_provider.get_secret(secret_path)
    except Exception as e:
        # We don't expose the underlying secret fetch error
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        ) from e

async def verify_tenant_access(
    tenant_id: Annotated[str, Path(description="The isolated tenant identifier")],
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    secrets_provider: SecretsProvider = Depends(get_secrets_provider),
) -> str:
    """Verify the provided Bearer token matches the tenant's API key.
    
    Raises 401 per GOV-005 standard error codes.
    Returns the tenant_id if valid.
    """
    expected_key = await get_tenant_api_key(tenant_id, secrets_provider)
    
    # Use constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(credentials.credentials, expected_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    return tenant_id

# Type alias for route handlers
TenantContext = Annotated[str, Depends(verify_tenant_access)]
