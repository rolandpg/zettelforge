"""Test skeletons for zettelforge.detection.explainer.

Phase 2: xfail placeholders for Phase 3 implementation.
"""

import pytest

XFAIL_REASON = "Phase 3 implementation pending — feat/detection-rules-first-class"


@pytest.mark.xfail(reason=XFAIL_REASON, strict=False)
def test_explain_returns_rule_explanation_shape() -> None:
    from zettelforge.detection.base import DetectionRule
    from zettelforge.detection.explainer import RuleExplanation, explain

    rule = DetectionRule(
        rule_id="test",
        title="t",
        source_format="sigma",
        content_sha256="0" * 64,
    )
    result = explain(rule)
    assert isinstance(result, RuleExplanation)
    assert result.schema_version == "1.0"


@pytest.mark.xfail(reason=XFAIL_REASON, strict=False)
def test_explain_populates_related_techniques() -> None:
    from zettelforge.detection.base import DetectionRule
    from zettelforge.detection.explainer import explain

    rule = DetectionRule(
        rule_id="test",
        title="t",
        source_format="sigma",
        content_sha256="0" * 64,
    )
    result = explain(rule)
    assert isinstance(result.related_techniques, list)


@pytest.mark.xfail(reason=XFAIL_REASON, strict=False)
def test_explain_handles_yara_rule_format() -> None:
    from zettelforge.detection.base import DetectionRule
    from zettelforge.detection.explainer import explain

    rule = DetectionRule(
        rule_id="test",
        title="t",
        source_format="yara",
        content_sha256="0" * 64,
    )
    result = explain(rule)
    assert result.model
