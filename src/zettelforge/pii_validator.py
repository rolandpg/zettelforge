"""PII detection and redaction using Microsoft Presidio (RFC-013).

Optional integration with ``GovernanceValidator``. When enabled via config,
scans content for PII before ``remember()`` operations and applies the
configured action (``log``, ``redact``, or ``block``).

This module is NOT imported at package init time. It is loaded lazily by
``GovernanceValidator`` only when ``governance.pii.enabled = true`` in
config. The core package never hard-depends on ``presidio-analyzer`` or
``spacy``.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from zettelforge.log import get_logger

_logger = get_logger("zettelforge.pii")


# PII entity types that are legitimate CTI indicators and should NOT be
# redacted by default. Users can override by specifying explicit entities.
_CTI_ALLOWLIST = frozenset(
    {
        "IP_ADDRESS",  # IOC — threat data, not PII
        "URL",  # IOC — threat data, not PII
        "DOMAIN_NAME",  # IOC — threat data, not PII
    }
)


@dataclass
class PIIDetection:
    """A single PII detection result."""

    entity_type: str
    text: str
    start: int
    end: int
    score: float


class PIIValidator:
    """Validates content for PII using Microsoft Presidio.

    Three actions:
        ``log`` (default) — detect and warn, pass content through unchanged.
        ``redact`` — replace detected PII with placeholders.
        ``block`` — raise :class:`PIIBlockedError` if ANY PII is detected.

    Thread-safe. Lazily loads Presidio + spaCy model on first call.
    The model downloads automatically (matching fastembed download pattern).
    """

    def __init__(
        self,
        action: str = "log",
        placeholder: str = "[REDACTED]",
        entities: Optional[List[str]] = None,
        language: str = "en",
        nlp_model: str = "en_core_web_sm",
    ) -> None:
        if action not in ("log", "redact", "block"):
            raise ValueError(f"Unknown PII action: {action!r}")
        self._action = action
        self._placeholder = placeholder
        # Filter out CTI allowlisted entities unless user explicitly included them
        self._entities: Optional[List[str]] = None
        if entities is not None:
            self._entities = [e for e in entities if e not in _CTI_ALLOWLIST]
        self._language = language
        self._nlp_model = nlp_model
        self._analyzer: object = None
        self._lock = threading.Lock()

    def _ensure_loaded(self) -> None:
        """Lazy-load Presidio analyzer (downloads spaCy model on first call)."""
        if self._analyzer is not None:
            return
        with self._lock:
            if self._analyzer is not None:
                return
            try:
                from presidio_analyzer import AnalyzerEngine
                from presidio_analyzer.nlp_engine import NlpEngineProvider
            except ImportError as exc:
                raise ImportError(
                    "PII validation requires presidio-analyzer. "
                    "Install with: pip install zettelforge[pii]"
                ) from exc

            configuration = {
                "nlp_engine_name": "spacy",
                "models": [
                    {"lang_code": self._language, "model_name": self._nlp_model},
                ],
            }
            provider = NlpEngineProvider(nlp_configuration=configuration)
            nlp_engine = provider.create_engine()
            self._analyzer = AnalyzerEngine(
                nlp_engine=nlp_engine,
                supported_languages=[self._language],
            )
            _logger.debug(
                "pii_analyzer_loaded",
                model=self._nlp_model,
                language=self._language,
            )

    def detect(self, text: str) -> List[PIIDetection]:
        """Analyze text and return detected PII entities.

        Results are sorted by start position and deduplicated by span
        (highest-score entity wins for overlapping positions).
        """
        if not text or not text.strip():
            return []
        self._ensure_loaded()
        results = self._analyzer.analyze(
            text=text,
            entities=self._entities,
            language=self._language,
        )
        # Deduplicate overlapping spans: keep highest score per (start, end)
        span_map: Dict[Tuple[int, int], PIIDetection] = {}
        for r in results:
            key = (r.start, r.end)
            existing = span_map.get(key)
            if existing is None or r.score > existing.score:
                span_map[key] = PIIDetection(
                    entity_type=r.entity_type,
                    text=text[r.start : r.end],
                    start=r.start,
                    end=r.end,
                    score=r.score,
                )
        return sorted(span_map.values(), key=lambda d: d.start)

    def validate(self, content: str) -> Tuple[bool, str, List[PIIDetection]]:
        """Validate content for PII.

        Args:
            content: Text to validate.

        Returns:
            Tuple of (passed, processed_content, detections).
            ``passed`` is True when action is not ``block`` or no PII found.
            ``processed_content`` is the original content (for ``log`` /
            ``block``) or redacted content (for ``redact``).
        """
        detections = self.detect(content)
        if not detections:
            return True, content, []

        _logger.warning(
            "pii_detected",
            count=len(detections),
            action=self._action,
            entities=[
                {"type": d.entity_type, "text": d.text, "score": round(d.score, 2)}
                for d in detections
            ],
        )

        if self._action == "redact":
            return True, self._redact(content, detections), detections

        if self._action == "block":
            types = ", ".join(sorted(set(d.entity_type for d in detections)))
            raise PIIBlockedError(
                f"Content blocked by PII validation: {len(detections)} "
                f"detections of types [{types}]. "
                f"Set governance.pii.action=log or governance.pii.action=redact "
                f"to allow storage."
            )

        # action == "log": warn only, pass through unchanged
        return True, content, detections

    def _redact(self, text: str, detections: List[PIIDetection]) -> str:
        """Replace detected PII spans with placeholders (reverse-order safe)."""
        result = list(text)
        for d in reversed(detections):
            result[d.start : d.end] = self._placeholder
        return "".join(result)


class PIIBlockedError(Exception):
    """Raised when content is blocked by PII validation (action=block)."""
