"""
Sigma rule parser — YAML load + JSON-schema validation.

Phase 3 implementation: ``yaml.safe_load`` + ``jsonschema.validate`` against
the vendored SigmaHQ schemas in ``zettelforge/sigma/schemas/``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def parse_file(path: str | Path) -> dict[str, Any]:
    """Parse a Sigma rule file into a validated dict.

    Phase 3 implementation: read YAML, validate against
    ``sigma-detection-rule-schema.json`` (or correlation/filter schema for
    those rule types), return the parsed dict.
    """
    raise NotImplementedError("zettelforge.sigma.parser.parse_file: Phase 3")


def parse_yaml(yaml_text: str) -> dict[str, Any]:
    """Parse Sigma YAML text into a validated dict.

    Phase 3 implementation: mirror of ``parse_file`` for in-memory strings.
    """
    raise NotImplementedError("zettelforge.sigma.parser.parse_yaml: Phase 3")
