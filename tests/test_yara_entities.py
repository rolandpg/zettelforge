"""Tests for zettelforge.yara.entities + cccs_metadata."""

from pathlib import Path

from zettelforge.yara.cccs_metadata import REQUIRED_FIELDS, validate_metadata
from zettelforge.yara.entities import from_rule_dict, rule_to_entities
from zettelforge.yara.parser import parse_file

FIXTURES = Path(__file__).parent / "fixtures" / "yara"


# ---------------------------------------------------------------------------
# rule_to_entities
# ---------------------------------------------------------------------------


def test_from_rule_dict_returns_yara_rule_entity() -> None:
    rule_dict = {"rule_name": "r", "meta": {}, "tags": []}
    entity, _relations = from_rule_dict(rule_dict)
    assert entity.source_format == "yara"
    assert entity.title == "r"


def test_from_rule_dict_emits_detects_edges_for_mitre_att() -> None:
    rule_dict = {"rule_name": "r", "meta": {"mitre_att": "T1218"}, "tags": []}
    _entity, relations = from_rule_dict(rule_dict)
    detects = [r for r in relations if r["rel"] == "detects"]
    assert len(detects) == 1
    assert detects[0]["to_type"] == "AttackPattern"
    assert detects[0]["to_props"]["technique_id"] == "T1218"


def test_cccs_compliance_tier_is_populated() -> None:
    rule_dict = {"rule_name": "r", "meta": {}, "tags": []}
    entity, _relations = from_rule_dict(rule_dict)
    assert entity.extra.get("cccs_compliant") in {"strict", "warn", "non_cccs"}


def test_technique_loader_fixture_produces_attack_pattern_relation() -> None:
    """Full-fixture path: parse → entities → the right relation graph."""
    rules = parse_file(FIXTURES / "technique_loader.yar")
    entity, relations = rule_to_entities(rules[0], tier="warn")
    assert entity.category == "TECHNIQUE"
    assert entity.technique_tag == "loader:memorymodule"

    detect_edges = [r for r in relations if r["rel"] == "detects"]
    assert any(e["to_props"]["technique_id"] == "T1218" for e in detect_edges)

    # CCCS meta also produced a YaraTag in the "technique" namespace.
    tech_tags = [
        r
        for r in relations
        if r["rel"] == "tagged_with"
        and r["to_type"] == "YaraTag"
        and r["to_props"].get("namespace") == "technique"
    ]
    assert tech_tags and tech_tags[0]["to_props"]["name"] == "loader:memorymodule"


def test_webshell_inline_tags_map_to_yara_tags() -> None:
    """Inline rule tags turn into YaraTag relations (category vs freeform)."""
    rules = parse_file(FIXTURES / "webshell.yar")
    _entity, relations = rule_to_entities(rules[0], tier="warn")
    tag_relations = [r for r in relations if r["rel"] == "tagged_with"]
    namespaces = {r["to_props"]["namespace"] for r in tag_relations}
    names = {r["to_props"]["name"] for r in tag_relations}
    # WEBSHELL is a known category token; ``php`` is freeform.
    assert "category" in namespaces
    assert "freeform" in namespaces
    assert "WEBSHELL" in names
    assert "php" in names


def test_content_sha256_is_stable_across_invocations() -> None:
    """Idempotency key — rule hash must not depend on dict ordering."""
    rule_a = parse_file(FIXTURES / "technique_loader.yar")[0]
    rule_b = parse_file(FIXTURES / "technique_loader.yar")[0]
    entity_a, _ = rule_to_entities(rule_a)
    entity_b, _ = rule_to_entities(rule_b)
    assert entity_a.content_sha256 == entity_b.content_sha256


# ---------------------------------------------------------------------------
# CCCS metadata validator — three-tier acceptance policy
# ---------------------------------------------------------------------------


def test_required_fields_includes_core_cccs_meta() -> None:
    """The authoritative list comes from CCCS_YARA.yml's ``optional`` column."""
    for mandatory in ("status", "sharing", "source", "author", "description", "category"):
        assert mandatory in REQUIRED_FIELDS
    # ``optional: Optional`` entries are also gated strict by design.
    for autogen in ("id", "fingerprint", "version", "modified"):
        assert autogen in REQUIRED_FIELDS


def test_strict_tier_rejects_missing_id() -> None:
    """Strict tier fails when a CCCS rule omits the ``id`` field."""
    # Full CCCS-ish metadata minus ``id``.
    meta = {
        "fingerprint": "a" * 64,
        "version": "1.0",
        "modified": "2024-01-01",
        "status": "RELEASED",
        "sharing": "TLP:WHITE",
        "source": "CCCS",
        "author": "analyst@CCCS",
        "description": "x",
        "category": "TECHNIQUE",
    }
    result = validate_metadata(meta, tier="strict")
    assert result.accepted is False
    assert any("id" in e for e in result.errors)


def test_warn_tier_accepts_missing_id_but_warns() -> None:
    meta = {"author": "x"}
    result = validate_metadata(meta, tier="warn")
    assert result.accepted is True
    assert any("id" in w for w in result.warnings)
    assert result.errors == []


def test_non_cccs_tier_accepts_empty_meta_silently() -> None:
    result = validate_metadata({}, tier="non_cccs")
    assert result.accepted is True
    assert result.warnings == []
    assert result.errors == []


def test_strict_tier_rejects_bad_field_values() -> None:
    """Strict tier validates values of present required fields."""
    meta = {
        "id": "valid_uuid_string_xxxxx",
        "fingerprint": "a" * 64,
        "version": "1.0",
        "modified": "2024-01-01",
        "author": "x@Y",
        "description": "x",
        "category": "TECHNIQUE",
        "status": "NOT_A_STATUS",  # bad value — not in rule_statuses
        "sharing": "TLP:WHITE",
        "source": "CCCS",
    }
    result = validate_metadata(meta, tier="strict")
    assert result.accepted is False
    assert any("status" in e for e in result.errors)
