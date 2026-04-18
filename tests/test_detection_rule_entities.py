"""Tests for the DetectionRule supertype dataclass (Phase 3)."""

from __future__ import annotations

import dataclasses

from zettelforge.detection.base import DetectionRule


def test_detection_rule_minimal_fields() -> None:
    rule = DetectionRule(
        rule_id="rule-1",
        title="Suspicious PowerShell",
        source_format="sigma",
        content_sha256="0" * 64,
    )
    assert rule.rule_id == "rule-1"
    assert rule.title == "Suspicious PowerShell"
    assert rule.source_format == "sigma"
    assert rule.content_sha256 == "0" * 64
    # Defaults
    assert rule.description is None
    assert rule.references == []
    assert rule.tags == []
    assert rule.extra == {}


def test_detection_rule_full_fields() -> None:
    rule = DetectionRule(
        rule_id="rule-2",
        title="WellFormed",
        source_format="yara",
        content_sha256="a" * 64,
        description="a yara test rule",
        author="SOC team",
        date="2026-04-17",
        modified="2026-04-17",
        references=["https://example/ref"],
        tags=["attack.t1059", "tlp.green"],
        level="high",
        status="stable",
        tlp="green",
        license="MIT",
        source_repo="https://github.com/example/rules",
        source_path="rules/yara/test.yar",
        extra={"custom": 1},
    )
    assert rule.tags == ["attack.t1059", "tlp.green"]
    assert rule.extra == {"custom": 1}


def test_explain_prompt_includes_title_format_and_tags() -> None:
    rule = DetectionRule(
        rule_id="r",
        title="Cobalt Strike Beacon",
        source_format="sigma",
        content_sha256="c" * 64,
        tags=["attack.t1071", "attack.command-and-control"],
    )
    prompt = rule.explain_prompt()
    assert "Cobalt Strike Beacon" in prompt
    assert "sigma" in prompt
    assert "attack.t1071" in prompt
    assert "attack.command-and-control" in prompt
    # Asks for the required JSON keys.
    for key in (
        "summary",
        "mechanism",
        "threat_model",
        "false_positive_patterns",
        "related_techniques",
        "confidence",
    ):
        assert key in prompt


def test_explain_prompt_handles_no_tags() -> None:
    rule = DetectionRule(
        rule_id="r",
        title="No tags here",
        source_format="yara",
        content_sha256="b" * 64,
    )
    prompt = rule.explain_prompt()
    assert "No tags here" in prompt
    assert "yara" in prompt
    assert "(none)" in prompt  # sentinel for empty tag list


def test_detection_rule_dataclass_roundtrip() -> None:
    rule = DetectionRule(
        rule_id="r",
        title="t",
        source_format="sigma",
        content_sha256="0" * 64,
        tags=["a", "b"],
        references=["http://x"],
    )
    d = dataclasses.asdict(rule)
    assert d["rule_id"] == "r"
    assert d["tags"] == ["a", "b"]
    # Round-trip: reconstruct from dict kwargs.
    rebuilt = DetectionRule(**d)
    assert rebuilt == rule
