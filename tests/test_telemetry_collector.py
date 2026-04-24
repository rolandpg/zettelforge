"""Unit tests for TelemetryCollector (RFC-007 / US-001).

Uses pytest's ``tmp_path`` for file I/O isolation so tests don't touch
``~/.amem/telemetry/`` and remain fully parallel-safe.
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

from zettelforge.telemetry import (
    TelemetryCollector,
    get_telemetry,
    reset_telemetry_for_testing,
)

# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture
def collector(tmp_path: Path) -> TelemetryCollector:
    """Fresh collector writing into an isolated tmp dir."""
    return TelemetryCollector(
        data_dir=str(tmp_path), logger_name="zettelforge.telemetry.test"
    )


@pytest.fixture
def debug_collector(tmp_path: Path) -> TelemetryCollector:
    """Collector whose logger is forced to DEBUG level."""
    name = "zettelforge.telemetry.test.debug"
    logging.getLogger(name).setLevel(logging.DEBUG)
    yield TelemetryCollector(data_dir=str(tmp_path), logger_name=name)
    logging.getLogger(name).setLevel(logging.NOTSET)


def _make_note(
    note_id: str = "note_abc",
    tier: str = "A",
    source_type: str = "mcp",
    domain: str = "cti",
    raw: str = "APT28 uses Cobalt Strike",
) -> Any:
    """Build a MemoryNote-shaped object via SimpleNamespace — avoids
    pulling in zettelforge.note_schema, keeps these unit tests hermetic.
    """
    return SimpleNamespace(
        id=note_id,
        content=SimpleNamespace(source_type=source_type, raw=raw),
        metadata=SimpleNamespace(tier=tier, domain=domain),
    )


def _read_jsonl(tmp_path: Path) -> List[Dict[str, Any]]:
    files = sorted(tmp_path.glob("telemetry_*.jsonl"))
    events: List[Dict[str, Any]] = []
    for f in files:
        for line in f.read_text().splitlines():
            if line.strip():
                events.append(json.loads(line))
    return events


# ── start_query ──────────────────────────────────────────────────────────


class TestStartQuery:
    def test_returns_uuid4_hex(self, collector: TelemetryCollector) -> None:
        qid = collector.start_query("what is apt28?", actor="vigil")
        assert isinstance(qid, str)
        assert len(qid) == 32
        assert int(qid, 16) >= 0  # pure hex

    def test_two_calls_yield_distinct_ids(self, collector: TelemetryCollector) -> None:
        a = collector.start_query("q1")
        b = collector.start_query("q2")
        assert a != b

    def test_actor_and_query_tracked_internally(
        self, collector: TelemetryCollector
    ) -> None:
        qid = collector.start_query("test-query", actor="vigil")
        ctx = collector._get_context(qid)
        assert ctx is not None
        assert ctx.actor == "vigil"
        assert ctx.query == "test-query"


# ── log_recall ──────────────────────────────────────────────────────────


class TestLogRecall:
    def test_writes_jsonl_info_mode(
        self, collector: TelemetryCollector, tmp_path: Path
    ) -> None:
        qid = collector.start_query("apt28 tools", actor="vigil")
        collector.log_recall(qid, [_make_note("n1"), _make_note("n2")], intent="factual")

        events = _read_jsonl(tmp_path)
        assert len(events) == 1
        e = events[0]
        assert e["event_type"] == "recall"
        assert e["query_id"] == qid
        assert e["actor"] == "vigil"
        assert e["query"] == "apt28 tools"
        assert e["result_count"] == 2
        assert "timestamp" in e
        assert "duration_ms" in e

    def test_info_mode_omits_debug_fields(
        self, collector: TelemetryCollector, tmp_path: Path
    ) -> None:
        qid = collector.start_query("q", actor="vigil")
        collector.log_recall(qid, [_make_note()], intent="factual")
        e = _read_jsonl(tmp_path)[0]
        for field in (
            "intent",
            "tier_distribution",
            "vector_latency_ms",
            "graph_latency_ms",
            "notes",
        ):
            assert field not in e, f"DEBUG field {field} leaked into INFO event"

    def test_debug_mode_adds_per_note_metadata(
        self, debug_collector: TelemetryCollector, tmp_path: Path
    ) -> None:
        qid = debug_collector.start_query("q", actor="vigil")
        notes = [
            _make_note("n1", tier="A", source_type="mcp", domain="cti"),
            _make_note("n2", tier="B", source_type="conversation", domain="general"),
        ]
        debug_collector.log_recall(
            qid, notes, intent="factual", vector_latency_ms=42, graph_latency_ms=18
        )
        e = _read_jsonl(tmp_path)[0]
        assert e["intent"] == "factual"
        assert e["vector_latency_ms"] == 42
        assert e["graph_latency_ms"] == 18
        assert e["tier_distribution"] == {"A": 1, "B": 1}
        assert e["notes"] == [
            {"id": "n1", "rank": 0, "tier": "A", "source_type": "mcp", "domain": "cti"},
            {
                "id": "n2",
                "rank": 1,
                "tier": "B",
                "source_type": "conversation",
                "domain": "general",
            },
        ]

    def test_accepts_enum_intent(
        self, debug_collector: TelemetryCollector, tmp_path: Path
    ) -> None:
        """intent may be a QueryIntent enum; collector stringifies via .value."""
        intent_enum = SimpleNamespace(value="temporal")
        qid = debug_collector.start_query("q")
        debug_collector.log_recall(qid, [_make_note()], intent=intent_enum)
        e = _read_jsonl(tmp_path)[0]
        assert e["intent"] == "temporal"

    def test_raw_note_content_never_stored(
        self, debug_collector: TelemetryCollector, tmp_path: Path
    ) -> None:
        secret = "SECRET_CONTENT_DO_NOT_LEAK"
        qid = debug_collector.start_query("q")
        debug_collector.log_recall(qid, [_make_note(raw=secret)], intent="factual")
        file_contents = (list(tmp_path.glob("telemetry_*.jsonl"))[0]).read_text()
        assert secret not in file_contents


# ── log_synthesis ────────────────────────────────────────────────────────


class TestLogSynthesis:
    def _synth_result(self, confidence: float = 0.72) -> Dict[str, Any]:
        return {
            "query": "apt28 tools",
            "synthesis": {"answer": "Cobalt Strike", "confidence": confidence},
            "metadata": {"sources_count": 3},
            "sources": [
                {"note_id": "n1", "tier": "A"},
                {"note_id": "n2", "tier": "B"},
                {"note_id": "n3", "tier": "B"},
            ],
        }

    def test_writes_synthesis_event(
        self, collector: TelemetryCollector, tmp_path: Path
    ) -> None:
        qid = collector.start_query("q", actor="vigil")
        collector.log_synthesis(qid, self._synth_result(), synthesis_latency_ms=2847)
        e = _read_jsonl(tmp_path)[0]
        assert e["event_type"] == "synthesis"
        assert e["query_id"] == qid
        assert e["actor"] == "vigil"
        assert e["result_count"] == 3

    def test_debug_mode_captures_confidence_and_citations(
        self, debug_collector: TelemetryCollector, tmp_path: Path
    ) -> None:
        qid = debug_collector.start_query("q")
        debug_collector.log_synthesis(qid, self._synth_result(0.91), synthesis_latency_ms=100)
        e = _read_jsonl(tmp_path)[0]
        assert e["confidence"] == pytest.approx(0.91)
        assert e["sources_count"] == 3
        assert e["cited_notes"] == ["n1", "n2", "n3"]
        assert e["synthesis_latency_ms"] == 100

    def test_tolerates_missing_synthesis_keys(
        self, debug_collector: TelemetryCollector, tmp_path: Path
    ) -> None:
        qid = debug_collector.start_query("q")
        # Minimal result — no 'synthesis', no 'metadata', no 'sources'
        debug_collector.log_synthesis(qid, {}, synthesis_latency_ms=0)
        e = _read_jsonl(tmp_path)[0]
        assert e["cited_notes"] == []
        assert e["sources_count"] == 0
        assert e["confidence"] is None

    def test_confidence_at_top_level_fallback(
        self, debug_collector: TelemetryCollector, tmp_path: Path
    ) -> None:
        qid = debug_collector.start_query("q")
        debug_collector.log_synthesis(qid, {"confidence": 0.5, "sources": []})
        e = _read_jsonl(tmp_path)[0]
        assert e["confidence"] == pytest.approx(0.5)


# ── log_feedback ─────────────────────────────────────────────────────────


class TestLogFeedback:
    def test_writes_feedback_event(
        self, collector: TelemetryCollector, tmp_path: Path
    ) -> None:
        qid = collector.start_query("q", actor="vigil")
        collector.log_feedback(qid, "note_xyz", utility=5, agent="vigil")
        e = _read_jsonl(tmp_path)[0]
        assert e["event_type"] == "feedback"
        assert e["note_id"] == "note_xyz"
        assert e["utility"] == 5
        assert e["agent"] == "vigil"


# ── auto_feedback_from_synthesis ─────────────────────────────────────────


class TestAutoFeedback:
    def test_only_runs_in_debug_mode(
        self, collector: TelemetryCollector, tmp_path: Path
    ) -> None:
        qid = collector.start_query("q", actor="vigil")
        collector.auto_feedback_from_synthesis(
            qid,
            retrieved_notes=[_make_note("n1")],
            synthesis_result={"sources": [{"note_id": "n1"}]},
        )
        # No feedback events should be written in INFO mode.
        assert _read_jsonl(tmp_path) == []

    def test_cited_notes_get_utility_4_uncited_get_2(
        self, debug_collector: TelemetryCollector, tmp_path: Path
    ) -> None:
        qid = debug_collector.start_query("q", actor="vigil")
        retrieved = [_make_note("n1"), _make_note("n2"), _make_note("n3")]
        synthesis = {"sources": [{"note_id": "n1"}, {"note_id": "n3"}]}
        debug_collector.auto_feedback_from_synthesis(qid, retrieved, synthesis)

        events = _read_jsonl(tmp_path)
        assert len(events) == 3
        utilities = {e["note_id"]: e["utility"] for e in events}
        assert utilities == {"n1": 4, "n2": 2, "n3": 4}
        for e in events:
            assert e["event_type"] == "feedback"
            assert e["agent"] == "vigil"


# ── Privacy / truncation ────────────────────────────────────────────────


class TestPrivacyAndTruncation:
    def test_query_truncated_to_200_in_info_mode(
        self, collector: TelemetryCollector, tmp_path: Path
    ) -> None:
        long_query = "x" * 500
        qid = collector.start_query(long_query)
        collector.log_recall(qid, [], intent="factual")
        e = _read_jsonl(tmp_path)[0]
        assert len(e["query"]) == 200

    def test_query_truncated_to_500_in_debug_mode(
        self, debug_collector: TelemetryCollector, tmp_path: Path
    ) -> None:
        long_query = "x" * 900
        qid = debug_collector.start_query(long_query)
        debug_collector.log_recall(qid, [], intent="factual")
        e = _read_jsonl(tmp_path)[0]
        assert len(e["query"]) == 500


# ── Lifecycle / file management ─────────────────────────────────────────


class TestLifecycle:
    def test_data_dir_autocreated_on_first_write(self, tmp_path: Path) -> None:
        nested = tmp_path / "does" / "not" / "exist"
        c = TelemetryCollector(data_dir=str(nested), logger_name="zettelforge.telemetry.test.x")
        qid = c.start_query("q")
        c.log_recall(qid, [], intent="factual")
        assert nested.is_dir()
        assert any(nested.glob("telemetry_*.jsonl"))

    def test_missing_start_query_is_graceful(
        self, collector: TelemetryCollector, tmp_path: Path
    ) -> None:
        """log_recall without a prior start_query still writes an event (no crash)."""
        collector.log_recall("unknown-qid", [_make_note()], intent="factual")
        e = _read_jsonl(tmp_path)[0]
        assert e["query_id"] == "unknown-qid"
        assert e["query"] == ""
        assert e["actor"] is None
        assert e["duration_ms"] == 0

    def test_concurrent_writes_do_not_corrupt(
        self, collector: TelemetryCollector, tmp_path: Path
    ) -> None:
        """Parallel log_recall calls must produce well-formed JSONL."""
        n_writes = 50
        qid = collector.start_query("q")

        def worker(i: int) -> None:
            collector.log_recall(qid, [_make_note(f"n{i}")], intent="factual")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(n_writes)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        events = _read_jsonl(tmp_path)
        assert len(events) == n_writes
        # Every line parsed as valid JSON; no half-written records.
        assert all(e["event_type"] == "recall" for e in events)


# ── Singleton ────────────────────────────────────────────────────────────


class TestSingleton:
    def test_get_telemetry_returns_same_instance(self) -> None:
        reset_telemetry_for_testing()
        try:
            a = get_telemetry()
            b = get_telemetry()
            assert a is b
        finally:
            reset_telemetry_for_testing()
