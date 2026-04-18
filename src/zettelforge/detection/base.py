"""
DetectionRule supertype dataclass.

Common contract shared by Sigma, YARA, and unknown-format detection rules.
See phase-1c-detection-rule-architecture.md §1.2 for field semantics.

Phase 2: scaffold only — field declarations used by Phase 3 ingest paths.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class DetectionRule:
    """Concrete, writeable supertype across detection-rule formats.

    Phase 3: ingest paths produce instances of this or its conceptual
    subtypes (``SigmaRule``, ``YaraRule``). In v1 the ontology is flat —
    subtypes are sibling entity types that share this field contract.
    """

    rule_id: str
    title: str
    source_format: str  # "sigma" | "yara" | "unknown"
    content_sha256: str
    description: Optional[str] = None
    author: Optional[str] = None
    date: Optional[str] = None
    modified: Optional[str] = None
    references: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    level: Optional[str] = None  # informational | low | medium | high | critical
    status: Optional[str] = None  # experimental | test | stable | deprecated
    tlp: Optional[str] = None
    license: Optional[str] = None
    source_repo: Optional[str] = None
    source_path: Optional[str] = None
    extra: dict[str, Any] = field(default_factory=dict)
