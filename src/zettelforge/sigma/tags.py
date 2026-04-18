"""
Sigma tag resolver — namespaced tags → typed entity references.

Phase 3 implementation: map ``attack.t1059`` → ``AttackPattern(T1059)``,
``cve.2021-44228`` → ``Vulnerability(CVE-2021-44228)``, ``tlp.amber`` →
unified TLP field, everything else → raw ``SigmaTag`` entity.
"""

from __future__ import annotations

from typing import Optional


def resolve_sigma_tag(raw_tag: str) -> tuple[str, Optional[str]]:
    """Resolve a Sigma tag string to ``(entity_type, entity_ref)``.

    Phase 3 implementation: returns ``("AttackPattern", "T1059")`` for
    ``attack.t1059``, ``("Vulnerability", "CVE-2021-44228")`` for
    ``cve.2021-44228``, or ``("SigmaTag", raw_tag)`` for unrecognised
    namespaces.
    """
    raise NotImplementedError("zettelforge.sigma.tags.resolve_sigma_tag: Phase 3")
