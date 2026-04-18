"""
YARA tag resolver — map loose inline tags to typed entity references.

YARA tags aren't namespaced in the grammar (a rule can declare
``rule Foo : APT MAL``); conventions vary between rule authors. This
resolver recognises a small set of well-known category tokens (see the
user's YARA-Style-Guide) and falls back to a freeform YaraTag otherwise.

Returns are always a tuple — callers can rely on getting something back
to store, so every tag leaves a trace in the graph even if we don't know
what it means.
"""

from __future__ import annotations

import re

# Category-style tokens recognised up-front. Uppercase form per YARA-Style-Guide
# convention but we match case-insensitively.
_CATEGORY_TOKENS: frozenset[str] = frozenset(
    {
        "APT",
        "CRIME",
        "CRIMEWARE",
        "EXPL",
        "HKTL",
        "MAL",
        "MALWARE",
        "PUA",
        "RAT",
        "RANSOM",
        "RANSOMWARE",
        "SUSP",
        "VULN",
        "WEBSHELL",
    }
)

_ATTACK_TAG_REGEX = re.compile(r"^(?:attack[._])?t(?P<id>\d{4}(?:\.\d{3})?)$", re.IGNORECASE)
_CVE_TAG_REGEX = re.compile(r"^cve[_-]?(?P<id>\d{4}[_-]\d{4,7})$", re.IGNORECASE)


def resolve_yara_tag(tag: str) -> tuple[str, dict[str, str]]:
    """Resolve a raw YARA tag into ``(entity_type, entity_properties)``.

    Never returns ``None``. Policies:

    * ``T####`` / ``attack.T####`` → ``("AttackPattern", {"technique_id": "T####"})``
    * ``CVE_2021_44228`` / ``CVE-2021-44228`` → ``("Vulnerability", {"cve_id": "CVE-YYYY-NNNN"})``
    * Known category token (``APT``, ``MAL``, …) → ``("YaraTag", {"namespace": "category", "name": TOKEN})``
    * Anything else → ``("YaraTag", {"namespace": "freeform", "name": tag})``
    """
    if not tag:
        return ("YaraTag", {"namespace": "freeform", "name": ""})

    stripped = tag.strip()

    m = _ATTACK_TAG_REGEX.match(stripped)
    if m:
        return ("AttackPattern", {"technique_id": "T" + m.group("id").upper()})

    m = _CVE_TAG_REGEX.match(stripped)
    if m:
        cve_id = "CVE-" + m.group("id").replace("_", "-")
        return ("Vulnerability", {"cve_id": cve_id.upper()})

    upper = stripped.upper()
    if upper in _CATEGORY_TOKENS:
        return ("YaraTag", {"namespace": "category", "name": upper})

    return ("YaraTag", {"namespace": "freeform", "name": stripped})


__all__ = ["resolve_yara_tag"]
