"""
YARA → entity/relation mapping.

Phase 3 implementation: translate a parsed YARA rule dict into a
``YaraRule`` entity plus the graph of typed relations described in
phase-1c-detection-rule-architecture.md §1.5.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from zettelforge.detection.base import DetectionRule


@dataclass
class YaraRule(DetectionRule):
    """``DetectionRule`` specialisation for YARA format.

    Adds grammar- and CCCS-derived fields on top of the shared contract.
    """

    cccs_id: Optional[str] = None
    fingerprint: Optional[str] = None  # SHA-256 over strings + condition
    category: Optional[str] = None  # INFO | EXPLOIT | TECHNIQUE | TOOL | MALWARE
    technique_tag: Optional[str] = None  # MITRE technique carried in CCCS meta
    cccs_version: Optional[str] = None
    hash_of_sample: list[str] = field(default_factory=list)
    rule_name: Optional[str] = None
    is_private: bool = False
    is_global: bool = False
    imports: list[str] = field(default_factory=list)
    condition: Optional[str] = None


def from_rule_dict(rule_dict: dict[str, Any]) -> tuple[YaraRule, list[dict[str, Any]]]:
    """Convert a parsed YARA rule dict to ``(YaraRule, relations)``.

    Phase 3 implementation: emit edges for ``detects`` (from ``mitre_att``),
    ``attributed_to`` (from ``actor``/``mitre_group``), ``tagged_with``
    (for every inline tag), ``references_cve`` (from reference meta or
    ``$cve_…`` strings).
    """
    raise NotImplementedError("zettelforge.yara.entities.from_rule_dict: Phase 3")
