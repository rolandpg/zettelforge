"""
Edition detection for ZettelForge.

Checks whether extensions (like zettelforge-enterprise) are available.
"""

import enum

from zettelforge.extensions import has_extension, reset_extensions


class Edition(enum.Enum):
    COMMUNITY = "community"
    ENTERPRISE = "enterprise"


class EditionError(Exception):
    """Raised when a feature requires an extension that is not installed."""

    pass


def is_enterprise() -> bool:
    """Check if enterprise extensions are available."""
    return has_extension("enterprise")


def is_community() -> bool:
    """Check if running without enterprise extensions."""
    return not has_extension("enterprise")


def get_edition() -> Edition:
    """Get the active edition."""
    return Edition.ENTERPRISE if is_enterprise() else Edition.COMMUNITY


def edition_name() -> str:
    """Return the edition display name."""
    if is_enterprise():
        return "ZettelForge + Extensions"
    return "ZettelForge"


def reset_edition() -> None:
    """Reset edition cache (for testing)."""
    reset_extensions()
