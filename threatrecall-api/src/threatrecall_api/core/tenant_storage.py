"""Tenant-scoped storage and MemoryManager factory.

Per GOV-019: Full isolation. Each tenant has:
- Isolated data directory: {data_dir}/tenants/{tenant_id}/
- Dedicated LanceDB instance
- Isolated notes.jsonl and entity_index.json
"""

from pathlib import Path
from typing import Optional

from threatrecall_api.core.config import settings

# Cache of MemoryManager instances per tenant
_managers: dict[str, object] = {}


def get_tenant_storage_path(tenant_id: str) -> Path:
    """Return the isolated storage path for a tenant."""
    return settings.tenant_storage_path / tenant_id


def get_memory_manager(tenant_id: str) -> object:
    """Get or create a MemoryManager for a tenant.

    MemoryManager is instantiated with per-tenant paths so each tenant's
    notes.jsonl and lance/ directory are fully isolated.

    Returns a MemoryManager instance from the local memory/ codebase.
    The import is deferred to avoid circular dependencies.
    """
    if tenant_id in _managers:
        return _managers[tenant_id]

    tenant_path = get_tenant_storage_path(tenant_id)
    tenant_path.mkdir(parents=True, exist_ok=True)

    # Import from bundled amem module
    import sys
    from pathlib import Path as P

    _amem_dir = P("/app/amem")
    if str(_amem_dir) not in sys.path:
        sys.path.insert(0, str(_amem_dir))

    from memory_manager import MemoryManager

    manager = MemoryManager(
        jsonl_path=str(tenant_path / "notes.jsonl"),
        lance_path=str(tenant_path / "lance"),
        cold_path=str(Path(settings.data_dir) / "cold"),
    )
    _managers[tenant_id] = manager
    return manager


def tenant_exists(tenant_id: str) -> bool:
    """Check if a tenant directory has been initialized."""
    return get_tenant_storage_path(tenant_id).exists()
