"""
Backend Factory -- creates the appropriate StorageBackend based on config.

Reads ZETTELFORGE_BACKEND env var (default: "sqlite").
Auto-detects if zettelforge.db exists in data_dir.
"""

import os

from zettelforge.log import get_logger
from zettelforge.storage_backend import StorageBackend

_logger = get_logger("zettelforge.backend_factory")


def get_storage_backend(data_dir: str | None = None) -> StorageBackend:
    """Create and return a StorageBackend based on environment config.

    Args:
        data_dir: Override data directory.  Falls back to AMEM_DATA_DIR / ~/.amem.

    Returns:
        An uninitialised StorageBackend (caller must call .initialize()).
    """
    from zettelforge.memory_store import get_default_data_dir

    resolved_dir = data_dir or str(get_default_data_dir())
    backend_env = os.environ.get("ZETTELFORGE_BACKEND", "sqlite").lower()

    if backend_env == "jsonl":
        _logger.warning(
            "jsonl_backend_not_implemented_using_sqlite",
            hint="Pure JSONL StorageBackend wrapper not yet available; using SQLite.",
        )

    from zettelforge.sqlite_backend import SQLiteBackend

    _logger.info("storage_backend_created", backend="sqlite", data_dir=resolved_dir)
    return SQLiteBackend(data_dir=resolved_dir)
