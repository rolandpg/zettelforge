"""
YARA rule parser — plyara wrapper.

Phase 3 implementation: wraps ``plyara.Plyara().parse_string`` and
normalises the output into a stable dict shape decoupled from plyara's
exact schema.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def parse_file(path: str | Path) -> list[dict[str, Any]]:
    """Parse a ``.yar``/``.yara`` file into a list of rule dicts.

    Phase 3 implementation: read file, hand to ``parse_text``.
    """
    raise NotImplementedError("zettelforge.yara.parser.parse_file: Phase 3")


def parse_text(yara_text: str) -> list[dict[str, Any]]:
    """Parse YARA rule text into a list of rule dicts.

    Phase 3 implementation: delegate to ``plyara.Plyara().parse_string``,
    promote CCCS-known metadata into typed keys, preserve unknown meta.
    """
    raise NotImplementedError("zettelforge.yara.parser.parse_text: Phase 3")
