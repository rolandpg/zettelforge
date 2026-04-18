"""Test skeletons for DetectionRule / SigmaRule / YaraRule entity shapes.

Phase 2: xfail placeholders for Phase 3 implementation.
"""

import pytest

XFAIL_REASON = "Phase 3 implementation pending — feat/detection-rules-first-class"


@pytest.mark.xfail(reason=XFAIL_REASON, strict=False)
def test_detection_rule_is_registered_entity_type() -> None:
    from zettelforge.ontology import ENTITY_TYPES

    assert "DetectionRule" in ENTITY_TYPES
    assert "SigmaRule" in ENTITY_TYPES
    assert "YaraRule" in ENTITY_TYPES
    raise NotImplementedError("Phase 3: assert full contract + round-trip via TypedEntityStore")


@pytest.mark.xfail(reason=XFAIL_REASON, strict=False)
def test_sigma_rule_subtype_inherits_common_fields() -> None:
    from zettelforge.sigma.entities import SigmaRule

    rule = SigmaRule(
        rule_id="sigma_test",
        title="test",
        source_format="sigma",
        content_sha256="0" * 64,
    )
    assert rule.logsource_product is None
    raise NotImplementedError("Phase 3: validate Sigma-specific field population")


@pytest.mark.xfail(reason=XFAIL_REASON, strict=False)
def test_yara_rule_subtype_inherits_common_fields() -> None:
    from zettelforge.yara.entities import YaraRule

    rule = YaraRule(
        rule_id="yara_test",
        title="test",
        source_format="yara",
        content_sha256="0" * 64,
    )
    assert rule.category is None
    raise NotImplementedError("Phase 3: validate YARA-specific field population")
