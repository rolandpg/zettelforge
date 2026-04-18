"""Tests for zettelforge.detection.explainer (Phase 3)."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from zettelforge.detection import explainer as explainer_mod
from zettelforge.detection.base import DetectionRule
from zettelforge.detection.explainer import (
    EXPLAIN_MAX_CALLS_PER_MINUTE,
    MAX_RULE_BODY_CHARS,
    RuleExplanation,
    SCHEMA_VERSION,
    explain,
    rate_limit_ok,
)


@pytest.fixture(autouse=True)
def _reset_rate_limiter() -> None:
    """Clear the module-level rate-limiter bucket between tests."""
    explainer_mod._reset_rate_limiter()
    yield
    explainer_mod._reset_rate_limiter()


def _rule(fmt: str = "sigma") -> DetectionRule:
    return DetectionRule(
        rule_id="test-rule",
        title="Test Rule",
        source_format=fmt,
        content_sha256="0" * 64,
        tags=["attack.t1059"],
    )


# ── Happy path ────────────────────────────────────────────────────────────────


def test_explain_parses_valid_json_from_llm() -> None:
    canned = json.dumps(
        {
            "summary": "Detects PowerShell encoded commands.",
            "mechanism": "Matches on -EncodedCommand flag in process creation.",
            "threat_model": "Used by commodity malware for evasion.",
            "false_positive_patterns": ["Legitimate admin scripts"],
            "related_techniques": ["T1059.001"],
            "confidence": 0.82,
        }
    )
    with patch.object(
        explainer_mod.llm_client, "generate", return_value=canned
    ) as mock_gen:
        result = explain(_rule(), rule_body="detection: sel1", provider="ollama")

    assert isinstance(result, RuleExplanation)
    assert result.summary == "Detects PowerShell encoded commands."
    assert result.mechanism.startswith("Matches on")
    assert result.false_positive_patterns == ["Legitimate admin scripts"]
    assert result.related_techniques == ["T1059.001"]
    assert result.confidence == pytest.approx(0.82)
    assert result.schema_version == SCHEMA_VERSION
    assert result.model == "ollama"
    assert result.generated_at  # ISO 8601 non-empty
    assert result.raw_response == canned
    # Sanity: prompt was called with json_mode=True and included the rule body.
    call_kwargs = mock_gen.call_args.kwargs
    assert call_kwargs["json_mode"] is True
    assert "detection: sel1" in mock_gen.call_args.args[0]


def test_explain_handles_markdown_fenced_json() -> None:
    canned = "```json\n" + json.dumps(
        {
            "summary": "s",
            "mechanism": "m",
            "threat_model": "tm",
            "false_positive_patterns": [],
            "related_techniques": [],
            "confidence": 0.5,
        }
    ) + "\n```"
    with patch.object(explainer_mod.llm_client, "generate", return_value=canned):
        result = explain(_rule(), rule_body="body", provider="ollama")
    assert result.summary == "s"
    assert result.confidence == pytest.approx(0.5)


# ── Failure fallbacks ─────────────────────────────────────────────────────────


def test_explain_returns_low_confidence_on_invalid_json() -> None:
    with patch.object(
        explainer_mod.llm_client, "generate", return_value="not json at all"
    ):
        result = explain(_rule(), rule_body="body", provider="ollama")
    assert result.confidence == 0.0
    assert "explanation unavailable" in result.summary
    assert "invalid json" in result.summary
    assert result.raw_response  # diagnostic copy preserved


def test_explain_returns_low_confidence_on_empty_llm_response() -> None:
    with patch.object(explainer_mod.llm_client, "generate", return_value=""):
        result = explain(_rule(), rule_body="body", provider="ollama")
    assert result.confidence == 0.0
    assert "empty response" in result.summary


def test_explain_returns_low_confidence_when_llm_raises() -> None:
    with patch.object(
        explainer_mod.llm_client, "generate", side_effect=RuntimeError("boom")
    ):
        result = explain(_rule(), rule_body="body", provider="ollama")
    assert result.confidence == 0.0
    assert "llm error" in result.summary
    assert "RuntimeError" in result.summary


def test_explain_coerces_bad_types_in_llm_response() -> None:
    # LLM returns correct keys but non-conforming value types.
    bad = json.dumps(
        {
            "summary": 42,  # wrong type
            "mechanism": None,
            "threat_model": "ok",
            "false_positive_patterns": "not a list",
            "related_techniques": ["T1", 99, None, "T2"],
            "confidence": "high",  # not a float
        }
    )
    with patch.object(explainer_mod.llm_client, "generate", return_value=bad):
        result = explain(_rule(), rule_body="body", provider="ollama")
    # Bad summary falls through to a diagnostic default.
    assert "explanation unavailable" in result.summary
    assert result.mechanism == ""  # None coerced to ""
    assert result.threat_model == "ok"
    assert result.false_positive_patterns == []  # wrong type dropped
    assert result.related_techniques == ["T1", "T2"]  # non-strings filtered
    assert result.confidence == 0.0  # bad value clamped


def test_explain_clamps_confidence_to_unit_interval() -> None:
    for raw_conf, expected in ((1.7, 1.0), (-0.3, 0.0), (0.6, 0.6)):
        canned = json.dumps(
            {
                "summary": "s",
                "mechanism": "m",
                "threat_model": "tm",
                "false_positive_patterns": [],
                "related_techniques": [],
                "confidence": raw_conf,
            }
        )
        with patch.object(explainer_mod.llm_client, "generate", return_value=canned):
            result = explain(_rule(), rule_body="body", provider="ollama")
        assert result.confidence == pytest.approx(expected)


# ── Mock-provider short-circuit ───────────────────────────────────────────────


def test_explain_mock_provider_returns_canned_response(monkeypatch) -> None:
    monkeypatch.setenv("ZETTELFORGE_LLM_PROVIDER", "mock")
    # When provider is "mock", the LLM must NOT be called at all.
    with patch.object(
        explainer_mod.llm_client, "generate", side_effect=AssertionError("should not be called")
    ):
        result = explain(_rule(), rule_body="body")
    assert result.confidence == 0.0
    assert result.summary == "mock provider — no real explanation"
    assert result.schema_version == SCHEMA_VERSION
    assert result.model.startswith("mock:")


def test_explain_provider_override_beats_env(monkeypatch) -> None:
    # Even if env says mock, passing provider="ollama" uses the real path.
    monkeypatch.setenv("ZETTELFORGE_LLM_PROVIDER", "mock")
    canned = json.dumps(
        {
            "summary": "real",
            "mechanism": "m",
            "threat_model": "t",
            "false_positive_patterns": [],
            "related_techniques": [],
            "confidence": 0.9,
        }
    )
    with patch.object(explainer_mod.llm_client, "generate", return_value=canned):
        result = explain(_rule(), rule_body="body", provider="ollama")
    assert result.summary == "real"


# ── Rate limiting ─────────────────────────────────────────────────────────────


def test_rate_limit_ok_returns_true_when_under_cap() -> None:
    assert rate_limit_ok() is True


def test_explain_returns_rate_limited_past_cap(monkeypatch) -> None:
    # Lower the cap so the test is fast.
    monkeypatch.setenv("ZETTELFORGE_EXPLAIN_RPM", "3")
    canned = json.dumps(
        {
            "summary": "s",
            "mechanism": "m",
            "threat_model": "t",
            "false_positive_patterns": [],
            "related_techniques": [],
            "confidence": 0.5,
        }
    )
    with patch.object(explainer_mod.llm_client, "generate", return_value=canned):
        results = [
            explain(_rule(), rule_body="body", provider="ollama") for _ in range(4)
        ]
    # First 3 succeed, the 4th is rate-limited.
    for r in results[:3]:
        assert r.summary == "s"
    assert results[3].confidence == 0.0
    assert "rate limited" in results[3].summary


def test_default_rate_limit_constant() -> None:
    # Sanity: the default hasn't drifted from the architecture target.
    assert EXPLAIN_MAX_CALLS_PER_MINUTE == 60


# ── Prompt injection / body truncation ────────────────────────────────────────


def test_explain_truncates_oversize_rule_body() -> None:
    giant_body = "A" * (MAX_RULE_BODY_CHARS + 5000)
    canned = json.dumps(
        {
            "summary": "s",
            "mechanism": "m",
            "threat_model": "t",
            "false_positive_patterns": [],
            "related_techniques": [],
            "confidence": 0.1,
        }
    )
    with patch.object(
        explainer_mod.llm_client, "generate", return_value=canned
    ) as mock_gen:
        explain(_rule(), rule_body=giant_body, provider="ollama")
    sent_prompt = mock_gen.call_args.args[0]
    # Truncation marker present; full oversize body not sent.
    assert "... [truncated]" in sent_prompt
    assert sent_prompt.count("A") <= MAX_RULE_BODY_CHARS + 1
