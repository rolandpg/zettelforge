"""
DetectionMatchConsumer protocol — deferred hook for external match events.

See phase-1c-detection-rule-architecture.md §4. The interface ships in v1
so ``MemoryManager.remember_match`` has a documented counterpart, but no
consumer implementation (Kafka, webhook, SIEM poll) lands in v1.

Phase 2: Protocol + TypedDict only. Phase 3 wires ``remember_match``.
"""

from __future__ import annotations

from typing import Protocol, TypedDict, runtime_checkable


class RuleMatchEvent(TypedDict, total=False):
    """External match event consumed by ``MemoryManager.remember_match``."""

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
    """Adapter from external match events to ``DetectionRule`` triggers.

    Implementations (DetectFlowKafkaConsumer v1.1, SiemWebhookReceiver v1.2+,
    SocPrimeAPIPoller enterprise v2.0+) do NOT ship in v1. Phase 3 may add
    a default base class; for Phase 2 the Protocol is enough.
    """

    def start(self) -> None:
        ...

    def stop(self) -> None:
        ...

    def on_match(self, event: RuleMatchEvent) -> None:
        ...
