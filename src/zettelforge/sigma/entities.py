"""
Sigma → entity/relation mapping.

Phase 3 implementation: translate a parsed Sigma rule dict into a
``SigmaRule`` entity plus the graph of typed relations described in
phase-1c-detection-rule-architecture.md §1.4.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from zettelforge.detection.base import DetectionRule


@dataclass
class SigmaRule(DetectionRule):
    """``DetectionRule`` specialisation for Sigma format.

    Adds Phase 1b Sigma-specific fields on top of the shared contract.
    """

    logsource_product: Optional[str] = None
    logsource_service: Optional[str] = None
    logsource_category: Optional[str] = None
    rule_level: Optional[str] = None  # raw Sigma ``level`` before enum mapping
    rule_status: Optional[str] = None  # raw Sigma ``status`` before enum mapping
    sigma_format_version: Optional[str] = None
    detection_body: Optional[str] = None
    rule_type: str = "detection"  # detection | correlation | filter
    fields: list[str] = field(default_factory=list)
    falsepositives: list[str] = field(default_factory=list)


def from_rule_dict(rule_dict: dict[str, Any]) -> tuple[SigmaRule, list[dict[str, Any]]]:
    """Convert a parsed Sigma rule dict to ``(SigmaRule, relations)``.

    Phase 3 implementation: emit edges for ``detects`` (from ATT&CK tags),
    ``references_cve`` (from CVE tags), ``tagged_with`` (for every tag),
    ``applies_to`` (LogSource), and ``related_to`` / ``superseded_by``
    (from the ``related`` field).
    """
    raise NotImplementedError("zettelforge.sigma.entities.from_rule_dict: Phase 3")
