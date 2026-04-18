"""
YARA → entity/relation mapping.

Translates a parsed YARA rule dict (as emitted by
:func:`zettelforge.yara.parser.parse_yara`) into:

* a :class:`YaraRule` dataclass carrying the grammar + CCCS-metadata
  fields the ontology cares about, and
* a list of relation tuples connecting the rule to typed entities
  (``AttackPattern`` for MITRE refs, ``ThreatActor`` for actor meta,
  ``YaraTag`` for inline tags + ``technique``).

Relations are plain dicts (``{"rel", "to_type", "to_props"}``) so the
caller can decide whether to write to the ontology store directly or pass
through ``MemoryManager``'s entity-hint path.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Optional

from zettelforge.detection.base import DetectionRule
from zettelforge.yara.cccs_metadata import ValidationResult, validate_metadata
from zettelforge.yara.tags import resolve_yara_tag


@dataclass
class YaraRule(DetectionRule):
    """``DetectionRule`` specialisation for YARA format."""

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _content_sha256(rule_dict: dict[str, Any]) -> str:
    """Hash a stable projection of the rule to detect exact duplicates.

    Uses the raw carved rule when available (from parser.py); falls back
    to a serialisation of ``rule_name + strings + condition`` otherwise.
    """
    raw = rule_dict.get("raw_rule")
    if raw:
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    parts: list[str] = [rule_dict.get("rule_name", "")]
    for s in rule_dict.get("strings", []) or []:
        if isinstance(s, dict):
            parts.append(f"{s.get('name', '')}={s.get('value', '')}")
    parts.extend(rule_dict.get("condition_terms", []) or [])
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def _coerce_hash_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    return [str(value)]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def rule_to_entities(
    rule: dict[str, Any],
    *,
    tier: str = "warn",
) -> tuple[YaraRule, list[dict[str, Any]]]:
    """Convert a parsed YARA rule dict to ``(YaraRule, relations)``.

    Args:
        rule: Output of :func:`parse_yara` for a single rule.
        tier: CCCS validation tier applied before extraction. The tier
            that the rule actually passed is recorded on
            ``entity.extra["cccs_compliant"]``.

    Relations schema (each is a dict)::

        {
            "rel": "detects" | "attributed_to" | "tagged_with",
            "to_type": "AttackPattern" | "ThreatActor" | "YaraTag" | "Vulnerability",
            "to_props": {...},
        }

    v1 follow-up: YARA ``imports`` (``pe``, ``hash``, ``dotnet``) are
    recorded as entity metadata only. They could become typed entities if
    we later want a capability-based retrieval axis.
    """
    meta: dict[str, Any] = rule.get("meta", {}) or {}
    rule_name = rule.get("rule_name") or "unknown_rule"

    # CCCS validation. ``non_cccs`` short-circuits to accepted.
    result: ValidationResult = validate_metadata(meta, tier=tier)  # type: ignore[arg-type]
    # The actual tier the rule is tagged with downstream:
    # * strict  — passed strict validation without errors
    # * warn    — warn tier (default) produced warnings or zero issues
    # * non_cccs — caller chose to skip validation entirely
    if tier == "non_cccs":
        compliance = "non_cccs"
    elif tier == "strict" and result.accepted and not result.errors:
        compliance = "strict"
    else:
        compliance = "warn"

    fingerprint = meta.get("fingerprint")
    cccs_id = meta.get("id")
    content_hash = _content_sha256(rule)

    entity = YaraRule(
        rule_id=cccs_id or rule_name,
        title=rule_name,
        source_format="yara",
        content_sha256=content_hash,
        description=meta.get("description"),
        author=meta.get("author"),
        date=meta.get("date"),
        modified=meta.get("modified"),
        references=[meta["report"]] if meta.get("report") else [],
        tags=list(rule.get("tags") or []),
        status=(str(meta["status"]).lower() if meta.get("status") else None),
        tlp=meta.get("sharing"),
        rule_name=rule_name,
        cccs_id=cccs_id,
        fingerprint=fingerprint,
        category=meta.get("category"),
        technique_tag=meta.get("technique"),
        cccs_version=str(meta["version"]) if meta.get("version") else None,
        hash_of_sample=_coerce_hash_list(meta.get("hash")),
        imports=list(rule.get("imports") or []),
        condition=(rule.get("raw_condition") or "").strip() or None,
        extra={
            "cccs_compliant": compliance,
            "cccs_warnings": list(result.warnings),
            "cccs_errors": list(result.errors),
            "condition_terms": list(rule.get("condition_terms") or []),
            "source_line_range": [rule.get("start_line"), rule.get("stop_line")],
        },
    )

    # Pull the source org into extra so downstream consumers can see it;
    # it's metadata only, not a separate entity.
    if meta.get("source"):
        entity.extra["source"] = meta["source"]
    if meta.get("malware_type"):
        entity.extra["malware_type"] = meta["malware_type"]

    relations: list[dict[str, Any]] = []

    # detects → AttackPattern (mitre_att meta). Normalize T1218, T1218.001.
    mitre = meta.get("mitre_att")
    if mitre:
        for token in _split_mitre(mitre):
            relations.append(
                {
                    "rel": "detects",
                    "to_type": "AttackPattern",
                    "to_props": {"technique_id": token},
                }
            )

    # tagged_with → YaraTag for the CCCS 'technique' meta (not a MITRE ID).
    technique = meta.get("technique")
    if technique:
        relations.append(
            {
                "rel": "tagged_with",
                "to_type": "YaraTag",
                "to_props": {"namespace": "technique", "name": str(technique)},
            }
        )

    # attributed_to → ThreatActor when meta.actor or meta.actor_type present.
    actor = meta.get("actor")
    actor_type = meta.get("actor_type")
    if actor:
        props: dict[str, Any] = {"name": str(actor)}
        if actor_type:
            props["aliases"] = []
            props["resource_level"] = str(actor_type)
        relations.append(
            {
                "rel": "attributed_to",
                "to_type": "ThreatActor",
                "to_props": props,
            }
        )
    elif actor_type:
        # Actor type without an actor name — still useful as metadata-only
        # hint; no relation emitted because ThreatActor.name is required.
        entity.extra["actor_type"] = str(actor_type)

    # tagged_with → YaraTag / AttackPattern / Vulnerability from inline tags.
    for raw_tag in rule.get("tags") or []:
        entity_type, entity_props = resolve_yara_tag(str(raw_tag))
        rel_name = "tagged_with"
        if entity_type == "AttackPattern":
            rel_name = "detects"
        elif entity_type == "Vulnerability":
            rel_name = "references_cve"
        relations.append(
            {"rel": rel_name, "to_type": entity_type, "to_props": entity_props}
        )

    return entity, relations


def from_rule_dict(rule: dict[str, Any]) -> tuple[YaraRule, list[dict[str, Any]]]:
    """Back-compat alias used by Phase 2 test scaffolding."""
    return rule_to_entities(rule)


def _split_mitre(value: Any) -> list[str]:
    """Normalize mitre_att meta which may be a string, list, or comma string."""
    if value is None:
        return []
    if isinstance(value, list):
        tokens = [str(v).strip() for v in value]
    else:
        tokens = [t.strip() for t in str(value).replace(";", ",").split(",")]
    return [t.upper() for t in tokens if t]


__all__ = ["YaraRule", "rule_to_entities", "from_rule_dict"]
