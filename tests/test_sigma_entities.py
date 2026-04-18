"""Test skeletons for zettelforge.sigma.entities.from_rule_dict.

Phase 2: xfail placeholders for Phase 3 implementation.
"""

import pytest

XFAIL_REASON = "Phase 3 implementation pending — feat/detection-rules-first-class"


@pytest.mark.xfail(reason=XFAIL_REASON, strict=False)
def test_from_rule_dict_returns_sigma_rule_entity() -> None:
    from zettelforge.sigma.entities import from_rule_dict

    rule_dict = {"title": "t", "logsource": {"category": "process_creation"}}
    entity, relations = from_rule_dict(rule_dict)
    assert entity.source_format == "sigma"


@pytest.mark.xfail(reason=XFAIL_REASON, strict=False)
def test_from_rule_dict_emits_detects_edges_for_attack_tags() -> None:
    from zettelforge.sigma.entities import from_rule_dict

    rule_dict = {"title": "t", "tags": ["attack.t1059"], "logsource": {}}
    _entity, relations = from_rule_dict(rule_dict)
    assert any(r.get("rel") == "detects" for r in relations)


@pytest.mark.xfail(reason=XFAIL_REASON, strict=False)
def test_from_rule_dict_emits_references_cve_edges() -> None:
    from zettelforge.sigma.entities import from_rule_dict

    rule_dict = {"title": "t", "tags": ["cve.2021-44228"], "logsource": {}}
    _entity, relations = from_rule_dict(rule_dict)
    assert any(r.get("rel") == "references_cve" for r in relations)
