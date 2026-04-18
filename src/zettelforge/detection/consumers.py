"""
DetectionMatchConsumer protocol — deferred hook for external match events.

See phase-1c-detection-rule-architecture.md §4 and phase-0-event-schema.md.

v1 ships ONLY the protocol + event TypedDict + an empty registry. Concrete
consumers (``DetectFlowKafkaConsumer`` v1.1, ``SiemWebhookReceiver`` v1.2+,
``SocPrimeAPIPoller`` enterprise v2.0+) do NOT ship in v1 — the interface
freezes here so those implementations don't reshape core APIs.
"""

from __future__ import annotations

from typing import Any, Protocol, TypedDict, runtime_checkable


class RuleMatchEvent(TypedDict, total=False):
    """External match event consumed by detection-match adapters.

    Mirrors the DetectFlow Phase 0 event schema fields relevant to core.
    """

    rule_id: str
    rule_title: str | None
    rule_format: str  # "sigma" | "yara" | "unknown"
    severity: str | None
    technique_ids: list[str]
    matched_at: str  # ISO 8601
    source_event: dict
    consumer: str  # "detectflow" | "splunk_webhook" | …


@runtime_checkable
class DetectionMatchConsumer(Protocol):
    """Adapter from external match events to note writes in a ``MemoryManager``.

    Implementations must be idempotent on ``(rule_id, match_payload.event_id)``
    so replayed / re-delivered events don't double-write notes.

    Lifecycle methods (``start``/``stop``) are optional — long-running
    consumers (Kafka pollers, webhook servers) use them; a synchronous
    adapter invoked from ``mm.remember_match`` can leave them as no-ops.
    """

    def consume_match(
        self,
        rule_id: str,
        match_payload: dict[str, Any],
        *,
        mm: Any,  # avoid circular import on MemoryManager
    ) -> str:
        """Ingest one match event. Returns the created note id.

        Implementations must be idempotent on
        ``(rule_id, match_payload.get("event_id"))``.
        """
        ...

    def start(self) -> None:
        """Begin streaming/polling (optional for synchronous consumers)."""
        ...

    def stop(self) -> None:
        """Halt streaming/polling and release resources."""
        ...

    def on_match(self, event: RuleMatchEvent) -> None:
        """Legacy hook retained for Phase-2 scaffolded callers. New
        implementations should prefer ``consume_match``."""
        ...


#: Registry populated by v1.1+ consumer implementations via entry points
#: or direct registration. Keys are short consumer names
#: (``"detectflow"``, ``"splunk_webhook"``, …); values are the consumer
#: class. Kept empty in v1 by design.
ALL_CONSUMERS: dict[str, type[DetectionMatchConsumer]] = {}
