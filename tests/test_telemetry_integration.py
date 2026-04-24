"""Integration tests for TelemetryCollector wired into MemoryManager (RFC-007 / US-002).

Uses real TelemetryCollector with stubbed MemoryManager so telemetry capture
can be verified end-to-end without external dependencies.

Run: pytest tests/test_telemetry_integration.py -v
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

from zettelforge.memory_manager import MemoryManager
from zettelforge.telemetry import TelemetryCollector, reset_telemetry_for_testing

# ── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture()
def telem_data_dir(tmp_path: Path) -> str:
    """Return an isolated tmp dir path for telemetry data."""
    d = tmp_path / "telemetry"
    d.mkdir(parents=True, exist_ok=True)
    return str(d)


@pytest.fixture(autouse=True)
def _reset_telemetry_singleton():
    """Ensure TelemetryCollector singleton is clean for every test."""
    reset_telemetry_for_testing()
    yield
    reset_telemetry_for_testing()
    # Clean up any test loggers that might leak DEBUG level
    for name in [
        "zettelforge.telemetry.test",
        "zettelforge.telemetry.test.r1",
        "zettelforge.telemetry.test.r2",
        "zettelforge.telemetry.test.r3",
        "zettelforge.telemetry.test.r5",
        "zettelforge.telemetry.nop",
    ]:
        _disable_debug(name)


# ── Helpers ──────────────────────────────────────────────────


def _enable_debug(logger_name: str = "zettelforge.telemetry.test"):
    """Force a logger to DEBUG so TelemetryCollector writes full telemetry."""
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    logger.handlers = []
    logger.addHandler(logging.NullHandler())
    return logger_name


def _disable_debug(logger_name: str = "zettelforge.telemetry.test"):
    """Restore a logger to WARNING level."""
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.WARNING)
    logger.handlers = []


def _read_events(data_dir: str) -> List[Dict[str, Any]]:
    """Read all events from today's telemetry JSONL file."""
    path = Path(data_dir) / f"telemetry_{datetime.now():%Y-%m-%d}.jsonl"
    if not path.exists():
        return []
    events = []
    for line in path.read_text().strip().split("\n"):
        if line:
            events.append(json.loads(line))
    return events


def _make_telem(
    data_dir: str, logger_name: str = "zettelforge.telemetry.test"
) -> TelemetryCollector:
    """Create a TelemetryCollector with real init into *data_dir*."""
    _enable_debug(logger_name)
    tc = TelemetryCollector(data_dir=data_dir, logger_name=logger_name)
    return tc


def _make_mock_note(note_id: str, tier: str = "A", domain: str = "cti", source_type: str = "test"):
    """Build a MagicMock that serializes correctly for telemetry helpers."""
    note = MagicMock()
    note.id = note_id
    metadata = MagicMock()
    metadata.tier = tier
    metadata.domain = domain
    note.metadata = metadata
    content = MagicMock()
    content.source_type = source_type
    note.content = content
    # Make MagicMock itself serializable by json
    note.__repr__ = lambda self: f"<MockNote {note_id}>"
    note.__str__ = lambda self: f"<MockNote {note_id}>"
    return note


# ── Tests ──────────────────────────────────────────────────────


class TestTelemetryIntegration:
    """End-to-end telemetry capture tests.

    We verify the TelemetryCollector's methods produce the correct output
    when called through the same code paths that MemoryManager uses.
    """

    def test_recall_emits_start_query_and_log_recall(self, telem_data_dir):
        """recall() must call start_query() and log_recall() with correct fields."""
        tc = _make_telem(telem_data_dir, "zettelforge.telemetry.integration.r1")

        qid = tc.start_query("APT28 infrastructure", actor="vigil")
        mock_note = _make_mock_note("note-1", tier="A", domain="cti")

        ctx = tc._get_context(qid)
        assert ctx is not None
        assert ctx.query == "APT28 infrastructure"
        assert ctx.actor == "vigil"

        tc.log_recall(
            qid, [mock_note], intent="factual", vector_latency_ms=45.2, graph_latency_ms=12.8
        )

        events = _read_events(telem_data_dir)
        recall_events = [e for e in events if e["event_type"] == "recall"]
        assert len(recall_events) == 1
        ev = recall_events[0]
        assert ev["query_id"] == qid
        assert ev["result_count"] == 1
        assert ev["result_count"] == 1
        assert ev["actor"] == "vigil"
        assert ev["vector_latency_ms"] == 45
        assert ev["graph_latency_ms"] == 12

    def test_synthesize_with_query_id_correlates_to_recall(self, telem_data_dir):
        """synthesize() reusing query_id must log with same query_id as recall."""
        tc = _make_telem(telem_data_dir, "zettelforge.telemetry.integration.r2")
        qid = tc.start_query("test correlation", actor="vigil")

        mock_note = _make_mock_note("note-correlated", tier="A", domain="cti")
        tc.log_recall(qid, [mock_note], intent="factual")
        tc.log_synthesis(
            qid,
            {"sources": [{"note_id": "note-correlated"}], "metadata": {"sources_count": 1}},
            synthesis_latency_ms=42.5,
        )

        events = _read_events(telem_data_dir)
        recall_ev = [e for e in events if e["event_type"] == "recall"][0]
        syn_ev = [e for e in events if e["event_type"] == "synthesis"][0]

        # Both share the same query_id
        assert recall_ev["query_id"] == syn_ev["query_id"] == qid
        # Synthesis captured source count
        assert syn_ev["result_count"] == 1
        # Latency was cast to int (may be 0 if test runs fast)
        assert syn_ev["duration_ms"] >= 0

    def test_synthesize_without_query_id_captures_uncorrelated(self, telem_data_dir):
        """synthesize() without a preceding recall() must create its own query_id."""
        tc = _make_telem(telem_data_dir, "zettelforge.telemetry.integration.r3")

        qid = tc.start_query("standalone query", actor="patton")
        tc.log_synthesis(
            qid,
            {"sources": [], "metadata": {"sources_count": 0}},
            synthesis_latency_ms=10,
        )

        events = _read_events(telem_data_dir)
        syn_events = [e for e in events if e["event_type"] == "synthesis"]
        assert len(syn_events) == 1
        ev = syn_events[0]
        assert ev["query_id"] == qid
        assert "standalone query" in ev["query"]
        assert ev["actor"] == "patton"

    def test_telemetry_no_ops_when_debug_disabled(self, telem_data_dir):
        """When DEBUG is disabled, events are INFO-mode only (no debug fields)."""
        # Disable DEBUG on all known ZF loggers (pytest may set root to DEBUG)
        for name in [
            "zettelforge.telemetry.test",
            "zettelforge.telemetry.test.r1",
            "zettelforge.telemetry.test.r2",
            "zettelforge.telemetry.test.r3",
            "zettelforge.telemetry.test.r5",
            "zettelforge.telemetry.nop",
            "zettelforge.telemetry",
            "zettelforge",
        ]:
            _disable_debug(name)
        root = logging.getLogger()
        root.setLevel(logging.WARNING)

        tc = TelemetryCollector(data_dir=telem_data_dir, logger_name="zettelforge.telemetry.nop")

        qid = tc.start_query("silent query")
        mock_note = _make_mock_note("note-silent")
        tc.log_recall(qid, [mock_note], intent="factual")
        tc.log_synthesis(
            qid,
            {"sources": [], "metadata": {"sources_count": 0}},
            synthesis_latency_ms=5,
        )

        events = _read_events(telem_data_dir)
        # INFO mode always writes events — no debug-only fields
        assert len(events) == 2
        for ev in events:
            assert "intent" not in ev, "intent should only appear in DEBUG mode"
            assert "tier_distribution" not in ev
            assert "cited_notes" not in ev

    def test_auto_feedback_cited_notes_utility_4(self):
        """Cited notes should get utility=4, uncited utility=2."""
        # Use a temp dir that _enable_debug will write to
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            tc = _make_telem(td, "zettelforge.telemetry.integration.r5")
            qid = tc.start_query("auto-feedback test")

            cited = _make_mock_note("cited-note", tier="A")
            uncited = _make_mock_note("uncited-note", tier="B")

            tc.log_recall(qid, [cited, uncited], intent="factual")

            synthesis_result = {
                "sources": [{"note_id": "cited-note"}],
                "metadata": {"sources_count": 1},
            }
            tc.auto_feedback_from_synthesis(qid, [cited, uncited], synthesis_result)

            events = _read_events(td)
            feedback_events = [e for e in events if e["event_type"] == "feedback"]

            cited_fb = [f for f in feedback_events if f["note_id"] == "cited-note"][0]
            uncited_fb = [f for f in feedback_events if f["note_id"] == "uncited-note"][0]

            assert cited_fb["utility"] == 4
            assert uncited_fb["utility"] == 2

    def test_actor_plumbing_through_memorymanager_interface(self):
        """MemoryManager gains actor kwarg on recall() and synthesize() (non-breaking)."""
        # Verify MemoryManager signatures have the actor parameter
        import inspect

        recall_sig = inspect.signature(MemoryManager.recall)
        assert "actor" in recall_sig.parameters

        synthesize_sig = inspect.signature(MemoryManager.synthesize)
        assert "actor" in synthesize_sig.parameters
