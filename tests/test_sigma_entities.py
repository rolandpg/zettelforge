"""Tests for zettelforge.sigma.entities.from_rule_dict.

Verifies the relation list emitted for each fixture and covers the
tag-namespace upgrades (ATT&CK / CVE / groups / TLP).
"""

from pathlib import Path

from zettelforge.sigma.entities import from_rule_dict, rule_to_entities
from zettelforge.sigma.parser import parse_file

FIXTURES = Path(__file__).parent / "fixtures" / "sigma"


def _rels_by_type(relations: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for r in relations:
        out.setdefault(r["rel"], []).append(r)
    return out


# ── Happy-path shape ─────────────────────────────────────────────────────────


def test_from_rule_dict_returns_sigma_rule_entity() -> None:
    rule_dict = {
        "title": "t",
        "logsource": {"category": "process_creation"},
        "detection": {"selection": {"a": "b"}, "condition": "selection"},
    }
    entity, relations = from_rule_dict(rule_dict)
    assert entity.source_format == "sigma"
    assert entity.title == "t"
    assert entity.logsource_category == "process_creation"
    # A minimal rule still emits at least a logsource edge.
    assert any(r["rel"] == "applies_to" for r in relations)


def test_rule_to_entities_is_alias_of_from_rule_dict() -> None:
    """Task brief uses ``rule_to_entities`` — verify it works as an alias."""
    assert rule_to_entities is from_rule_dict


# ── Tag upgrades ─────────────────────────────────────────────────────────────


def test_from_rule_dict_emits_detects_edges_for_attack_tags() -> None:
    rule_dict = {
        "title": "t",
        "tags": ["attack.t1059"],
        "logsource": {},
        "detection": {"selection": {"a": "b"}, "condition": "selection"},
    }
    entity, relations = from_rule_dict(rule_dict)
    by = _rels_by_type(relations)
    # The raw SigmaTag edge stays for provenance AND a typed detects edge.
    assert any(r["to_value"] == "attack.t1059" for r in by.get("tagged_with", []))
    assert any(r["to_value"] == "T1059" for r in by.get("detects", []))


def test_from_rule_dict_emits_references_cve_edges() -> None:
    rule_dict = {
        "title": "t",
        "tags": ["cve.2021-44228"],
        "logsource": {},
        "detection": {"selection": {"a": "b"}, "condition": "selection"},
    }
    entity, relations = from_rule_dict(rule_dict)
    by = _rels_by_type(relations)
    assert any(r["to_value"] == "CVE-2021-44228" for r in by.get("references_cve", []))


def test_from_rule_dict_emits_attributed_to_for_group_tags() -> None:
    rule_dict = {
        "title": "t",
        "tags": ["attack.g0007"],
        "logsource": {},
        "detection": {"selection": {"a": "b"}, "condition": "selection"},
    }
    _entity, relations = from_rule_dict(rule_dict)
    by = _rels_by_type(relations)
    # ATT&CK group IDs upgrade to IntrusionSet, not AttackPattern.
    assert by.get("attributed_to")
    assert by["attributed_to"][0]["to_type"] == "IntrusionSet"
    assert by["attributed_to"][0]["to_value"] == "G0007"
    assert "detects" not in by


def test_tlp_tag_is_metadata_only() -> None:
    """``tlp.amber`` must stay as a raw SigmaTag — no typed upgrade."""
    rule_dict = {
        "title": "t",
        "tags": ["tlp.amber"],
        "logsource": {},
        "detection": {"selection": {"a": "b"}, "condition": "selection"},
    }
    _entity, relations = from_rule_dict(rule_dict)
    by = _rels_by_type(relations)
    assert any(r["to_value"] == "tlp.amber" for r in by.get("tagged_with", []))
    # No detects / references_cve / attributed_to upgrade for TLP.
    for rel in ("detects", "references_cve", "attributed_to"):
        assert rel not in by, f"{rel} should not fire for tlp.*"


# ── Per-fixture assertions ───────────────────────────────────────────────────


def test_process_creation_fixture_emits_expected_relations() -> None:
    rule = parse_file(FIXTURES / "process_creation_example.yml")
    entity, relations = from_rule_dict(rule)
    by = _rels_by_type(relations)
    # Two logsource facets: product=windows + category=process_creation.
    applies = by.get("applies_to", [])
    assert len(applies) == 2
    assert {r["to_value"] for r in applies} == {
        "product:windows",
        "category:process_creation",
    }
    # Fixture has no tags / no related — nothing else to emit.
    assert "tagged_with" not in by
    assert "detects" not in by
    # Fixture has no id → content-hash-derived id prefix.
    assert entity.rule_id.startswith("sigma_")


def test_cloud_fixture_emits_product_and_service_edges() -> None:
    rule = parse_file(FIXTURES / "cloud_example.yml")
    entity, relations = from_rule_dict(rule)
    by = _rels_by_type(relations)
    assert entity.rule_id == "929a690e-bef0-4204-a928-ef5e620d6fcb"
    assert entity.logsource_service == "security"
    values = {r["to_value"] for r in by.get("applies_to", [])}
    assert values == {"product:windows", "service:security"}


def test_correlation_fixture_marked_as_correlation_rule() -> None:
    rule = parse_file(FIXTURES / "correlation_example.yml")
    entity, relations = from_rule_dict(rule)
    assert entity.rule_type == "correlation"
    # Correlation rules have no logsource/tags in this fixture.
    assert relations == []
    assert entity.detection_body  # detection_body captures the correlation block


def test_tagged_fixture_emits_full_upgrade_matrix() -> None:
    """Exercises every tag namespace we upgrade — ATT&CK technique,
    sub-technique, group, CVE — plus TLP passthrough. Proves provenance
    (raw ``tagged_with``) always co-exists with the typed edge."""
    rule = parse_file(FIXTURES / "tagged_example.yml")
    entity, relations = from_rule_dict(rule)
    by = _rels_by_type(relations)

    assert entity.rule_id == "7e3d88a2-bfaa-4f52-9e0b-2bbbdd0d4ea1"
    assert entity.rule_level == "critical"
    assert entity.falsepositives  # carried through
    assert entity.fields == ["CommandLine", "ProcessName"]

    # Every raw tag is preserved.
    tagged = {r["to_value"] for r in by.get("tagged_with", [])}
    assert tagged == {
        "attack.t1190",
        "attack.t1059.001",
        "attack.g0007",
        "cve.2021-44228",
        "tlp.amber",
    }
    # Technique + sub-technique both emit detects edges.
    detects = {r["to_value"] for r in by.get("detects", [])}
    assert detects == {"T1190", "T1059.001"}
    # CVE namespace upgrades to Vulnerability with canonical id.
    cves = {r["to_value"] for r in by.get("references_cve", [])}
    assert cves == {"CVE-2021-44228"}
    # Group → IntrusionSet.
    attrib = {r["to_value"] for r in by.get("attributed_to", [])}
    assert attrib == {"G0007"}


# ── ``related:`` block ───────────────────────────────────────────────────────


def test_related_obsolete_maps_to_superseded_by() -> None:
    rule_dict = {
        "title": "t",
        "logsource": {},
        "detection": {"selection": {"a": "b"}, "condition": "selection"},
        "related": [
            {"id": "aaaa1111-0000-0000-0000-000000000001", "type": "obsolete"},
            {"id": "bbbb2222-0000-0000-0000-000000000002", "type": "derived"},
        ],
    }
    _entity, relations = from_rule_dict(rule_dict)
    by = _rels_by_type(relations)
    assert by["superseded_by"][0]["to_value"].startswith("aaaa1111")
    assert by["related_to"][0]["to_value"].startswith("bbbb2222")
