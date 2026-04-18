"""
ZettelForge Detection Rules — shared supertype + explainer + consumers.

Phase 2 scaffold: exports only. Phase 3 fills implementations.
See: phase-1c-detection-rule-architecture.md
"""

from zettelforge.detection.base import DetectionRule
from zettelforge.detection.consumers import DetectionMatchConsumer, RuleMatchEvent
from zettelforge.detection.explainer import RuleExplanation, explain

__all__ = [
    "DetectionRule",
    "DetectionMatchConsumer",
    "RuleExplanation",
    "RuleMatchEvent",
    "explain",
]
