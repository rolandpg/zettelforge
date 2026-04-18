"""
CCCS YARA metadata validator — clean-room re-implementation.

Upstream ``validator_functions.py`` is intentionally NOT vendored (see
phase-1c-detection-rule-architecture.md §2.1). Phase 3 implements the
subset we care about: ``valid_uuid``, ``valid_version``, ``valid_date``,
``valid_mitre_att``, category/child relationships, SHA hash regexes.
"""

from __future__ import annotations

from typing import Any


def validate_metadata(rule: dict[str, Any], tier: str = "strict") -> tuple[str, list[str]]:
    """Validate CCCS meta on a parsed YARA rule.

    Returns ``(compliance, warnings)`` where ``compliance`` is one of
    ``"strict"``, ``"warn"``, or ``"non_cccs"`` (§1.5 three-tier accept
    policy).

    Phase 3 implementation: walk the vendored ``CCCS_YARA.yml`` spec,
    check required/optional meta per the ``tier`` gate, validate each
    value through the locally-implemented validator functions.
    """
    raise NotImplementedError("zettelforge.yara.cccs_metadata.validate_metadata: Phase 3")
