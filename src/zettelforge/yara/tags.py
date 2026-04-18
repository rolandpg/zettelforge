"""
YARA tag resolver — heuristic tag → typed entity reference.

YARA tags are not namespaced. Phase 3 implementation falls back to
heuristics: ``t1059`` / ``T1059`` / ``attack.T1059`` → ``AttackPattern``,
``cve_2021_44228`` / ``CVE-2021-44228`` → ``Vulnerability``, else raw
``YaraTag``.
"""

from __future__ import annotations

from typing import Optional


def resolve_yara_tag(raw_tag: str) -> tuple[str, Optional[str]]:
    """Resolve a YARA tag string to ``(entity_type, entity_ref)``.

    Phase 3 implementation: regex match against ATT&CK and CVE patterns
    with a final fallback to a ``YaraTag`` raw-tag entity.
    """
    raise NotImplementedError("zettelforge.yara.tags.resolve_yara_tag: Phase 3")
