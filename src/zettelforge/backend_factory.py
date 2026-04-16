"""
Backend Factory -- creates the appropriate StorageBackend based on config.

Reads ZETTELFORGE_BACKEND env var (default: "sqlite").
Auto-detects if zettelforge.db exists in data_dir.
"""

import os
import warnings
from pathlib import Path

from zettelforge.log import get_logger
from zettelforge.storage_backend import StorageBackend

_logger = get_logger("zettelforge.backend_factory")


def _check_jsonl_migration(data_dir: str) -> None:
    """Warn users with existing JSONL data that migration is needed."""
    notes_jsonl = Path(data_dir) / "notes.jsonl"
    zettelforge_db = Path(data_dir) / "zettelforge.db"
    if notes_jsonl.exists() and not zettelforge_db.exists():
        msg = (
            f"Found existing JSONL data at {notes_jsonl} but no SQLite database. "
            "ZettelForge 2.2.0 defaults to SQLite. Run the migration script to "
            "preserve your data:\n\n"
            "  python -m zettelforge.scripts.migrate_jsonl_to_sqlite\n\n"
            "Or set ZETTELFORGE_BACKEND=jsonl to continue using JSONL (deprecated). "
            "See CHANGELOG.md for details."
        )
        warnings.warn(msg, FutureWarning, stacklevel=3)
        _logger.warning("jsonl_migration_needed", notes_jsonl=str(notes_jsonl))


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
    else:
        _check_jsonl_migration(resolved_dir)

    from zettelforge.sqlite_backend import SQLiteBackend

    _logger.info("storage_backend_created", backend="sqlite", data_dir=resolved_dir)
    return SQLiteBackend(data_dir=resolved_dir)
