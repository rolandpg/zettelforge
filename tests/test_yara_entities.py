"""Test skeletons for zettelforge.yara.entities.from_rule_dict.

Phase 2: xfail placeholders for Phase 3 implementation.
"""

import pytest

XFAIL_REASON = "Phase 3 implementation pending — feat/detection-rules-first-class"


@pytest.mark.xfail(reason=XFAIL_REASON, strict=False)
def test_from_rule_dict_returns_yara_rule_entity() -> None:
    from zettelforge.yara.entities import from_rule_dict

    rule_dict = {"rule_name": "r", "meta": {}, "tags": []}
    entity, _relations = from_rule_dict(rule_dict)
    assert entity.source_format == "yara"


@pytest.mark.xfail(reason=XFAIL_REASON, strict=False)
def test_from_rule_dict_emits_detects_edges_for_mitre_att() -> None:
    from zettelforge.yara.entities import from_rule_dict

    rule_dict = {"rule_name": "r", "meta": {"mitre_att": "T1218"}, "tags": []}
    _entity, relations = from_rule_dict(rule_dict)
    assert any(r.get("rel") == "detects" for r in relations)


@pytest.mark.xfail(reason=XFAIL_REASON, strict=False)
def test_cccs_compliance_tier_is_populated() -> None:
    from zettelforge.yara.entities import from_rule_dict

    rule_dict = {"rule_name": "r", "meta": {}, "tags": []}
    entity, _relations = from_rule_dict(rule_dict)
    assert entity.extra.get("cccs_compliant") in {"strict", "warn", "non_cccs"}
