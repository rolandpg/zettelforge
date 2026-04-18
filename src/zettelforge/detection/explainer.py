"""
LLM-generated rule explainer — the v1 killer feature.

See phase-1c-detection-rule-architecture.md §3 for the full spec.

Phase 2: dataclass shape + stubbed ``explain`` signature. Phase 3 wires the
LLM provider, prompt dispatch, JSON-mode parsing, and retry/backoff.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zettelforge.detection.base import DetectionRule


@dataclass
class RuleExplanation:
    """Structured explanation emitted by the LLM explainer.

    See §3a of the Phase 1c architecture for schema rationale.
    """

    summary: str
    mechanism: str
    threat_model: str
    false_positive_patterns: list[str] = field(default_factory=list)
    related_techniques: list[str] = field(default_factory=list)
    confidence: float = 0.0
    model: str = ""
    generated_at: str = ""
    schema_version: str = "1.0"


def explain(rule: "DetectionRule") -> RuleExplanation:
    """Produce a ``RuleExplanation`` for a detection rule.

    Phase 3 implementation: invokes the configured LLM provider with a
    format-aware prompt (Sigma YAML vs. YARA grammar), parses JSON-mode
    response, retries once on parse failure, and falls back to a stub
    explanation on persistent failure.
    """
    raise NotImplementedError("zettelforge.detection.explainer.explain: Phase 3")
