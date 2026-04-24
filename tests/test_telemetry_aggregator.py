"""Tests for telemetry_aggregator.py (RFC-007 / US-003)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

import pytest

from zettelforge.scripts.telemetry_aggregator import (
    _aggregate,
    _load_events,
    main,
)


DATE = "2026-04-23"


def _recall(
    query_id: str = "q1",
    result_count: int = 5,
    duration_ms: int = 150,
    tier_dist: Dict[str, int] | None = None,
    notes: List[Dict[str, Any]] | None = None,
    actor: str | None = "vigil",
) -> Dict[str, Any]:
    return {
        "event_type": "recall",
        "query_id": query_id,
        "actor": actor,
        "result_count": result_count,
        "duration_ms": duration_ms,
        "query": "test query",
        "tier_distribution": tier_dist or {},
        "notes": notes or [],
    }


def _synthesis(
    query_id: str = "q1",
    sources_count: int = 3,
    duration_ms: int = 2500,
    confidence: float = 0.75,
    cited_notes: List[str] | None = None,
) -> Dict[str, Any]:
    return {
        "event_type": "synthesis",
        "query_id": query_id,
        "result_count": sources_count,
        "duration_ms": duration_ms,
        "confidence": confidence,
        "cited_notes": cited_notes or [],
    }


def _feedback(
    query_id: str = "q1",
    note_id: str = "note-1",
    utility: int = 4,
) -> Dict[str, Any]:
    return {
        "event_type": "feedback",
        "query_id": query_id,
        "note_id": note_id,
        "utility": utility,
    }


def test_missing_day_returns_empty_report(tmp_path: Path):
    events = _load_events(str(tmp_path), "2099-01-01")
    report = _aggregate(events, "2099-01-01", str(tmp_path))
    assert report["total_queries"] is None
    assert report["date"] == "2099-01-01"
    assert report["tier_distribution"] == {}


def test_aggregates_recall_and_synthesis(tmp_path: Path):
    events = [
        _recall("q1", result_count=5, duration_ms=100),
        _recall("q2", result_count=3, duration_ms=200),
        _synthesis("q1", confidence=0.8),
        _synthesis("q2", confidence=0.6),
    ]
    report = _aggregate(events, DATE, str(tmp_path))

    assert report["total_queries"] == 2  # two unique query_ids
    assert report["total_synthesis"] == 2
    assert report["avg_recall_latency_ms"] == 150.0
    assert report["avg_synthesis_latency_ms"] == 2500.0
    assert report["avg_confidence"] == 0.7
    assert report["notes_per_query"] == 4.0


def test_tier_distribution_merges_across_events(tmp_path: Path):
    events = [
        _recall("q1", tier_dist={"A": 3, "B": 2}),
        _recall("q2", tier_dist={"A": 2, "C": 1}),
    ]
    # Also add per-note tier counts
    notes = [
        {"id": "n1", "tier": "A"},
        {"id": "n2", "tier": "A"},
        {"id": "n3", "tier": "B"},
    ]
    events[0]["notes"] = notes

    report = _aggregate(events, DATE, str(tmp_path))

    # tier_dist counts (3+2) + per-note tier counts (2) = 7
    assert report["tier_distribution"]["A"] == 7
    assert report["tier_distribution"]["B"] == 3  # 2 from tier_dist + 1 from notes
    assert report["tier_distribution"]["C"] == 1


def test_feedback_utility_and_top_notes(tmp_path: Path):
    events = [
        _recall("q1", result_count=3, duration_ms=100),
        _synthesis("q1", cited_notes=["cited-note-1"]),
        _feedback("q1", "cited-note-1", utility=4),
        _feedback("q1", "cited-note-2", utility=2),
        _feedback("q1", "cited-note-1", utility=5),
    ]
    report = _aggregate(events, DATE, str(tmp_path))

    assert report["feedback_count"] == 3
    assert report["avg_utility"] == pytest.approx(3.67, abs=0.01)
    assert "cited-note-1" in report["top_utility_notes"]


def test_unused_notes_count(tmp_path: Path):
    events = [
        _recall(
            "q1",
            notes=[
                {"id": "note-a", "tier": "A", "source_type": "cti"},
                {"id": "note-b", "tier": "B", "source_type": "cti"},
                {"id": "note-c", "tier": "B", "source_type": "cti"},
            ],
        ),
        _synthesis("q1", cited_notes=["note-a"]),
    ]
    report = _aggregate(events, DATE, str(tmp_path))
    assert report["unused_notes_count"] == 2  # note-b and note-c were retrieved but never cited
