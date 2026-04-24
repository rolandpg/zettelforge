"""Tests for telemetry_dashboard.py data processing (RFC-007 / US-005)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pytest

from zettelforge.scripts.telemetry_dashboard import (
    _latency_df,
    _query_volume_df,
    _read_all_events,
    _tier_distribution_df,
    _unused_notes_summary,
    _utility_df,
    _percentile,
)


def _recall_event(
    date: str = "2026-04-22",
    query_id: str = "q1",
    duration_ms: int = 150,
    tier_dist: Dict[str, int] | None = None,
    notes: list[Dict[str, Any]] | None = None,
    cited: list[str] | None = None,
) -> Dict[str, Any]:
    return {
        "event_type": "recall",
        "query_id": query_id,
        "duration_ms": duration_ms,
        "tier_distribution": tier_dist or {},
        "notes": notes or [],
        "cited_notes": cited or [],
        "_date": date,
    }


def _feedback_event(date: str = "2026-04-22", utility: int = 4) -> Dict[str, Any]:
    ev = {
        "event_type": "feedback",
        "utility": utility,
    }
    if date:
        ev["_date"] = date
    return ev


def _write_events(tmp_path: Path, events: list[Dict[str, Any]]) -> str:
    """Write events grouped by date into telemetry JSONL files."""
    by_date: dict[str, list[str]] = {}
    for ev in events:
        ts = ev.get("_date", "2026-04-22")
        by_date.setdefault(ts, []).append(json.dumps(ev))
    for date, lines in by_date.items():
        (tmp_path / f"telemetry_{date}.jsonl").write_text("\n".join(lines) + "\n")
    return str(tmp_path)


class TestReadAllEvents:
    def test_returns_all_events(self, tmp_path: Path):
        events = [
            {"event_type": "recall", "query_id": "q1"},
            {"event_type": "feedback", "utility": 4},
        ]
        data_dir = _write_events(tmp_path, events)
        result = _read_all_events(data_dir)
        assert len(result) == 2

    def test_returns_empty_on_missing_dir(self):
        result = _read_all_events("/nonexistent/telemetry")
        assert result == []


class TestQueryVolume:
    def test_counts_queries_per_day(self, tmp_path: Path):
        events = [
            _recall_event("2026-04-22", "q1"),
            _recall_event("2026-04-22", "q2"),
            _recall_event("2026-04-23", "q3"),
        ]
        data_dir = _write_events(tmp_path, events)
        all_events = _read_all_events(data_dir)
        df = _query_volume_df(all_events)
        assert df is not None
        assert df["queries"].tolist() == [2, 1]

    def test_returns_none_without_recall_events(self, tmp_path: Path):
        events = [{"event_type": "feedback", "utility": 4}]
        data_dir = _write_events(tmp_path, events)
        all_events = _read_all_events(data_dir)
        df = _query_volume_df(all_events)
        assert df is None


class TestLatencyDf:
    def test_computes_p50_p95(self, tmp_path: Path):
        durations = [100, 200, 300, 400, 500]
        events = [_recall_event("2026-04-22", f"q{i}", dur) for i, dur in enumerate(durations, 1)]
        data_dir = _write_events(tmp_path, events)
        all_events = _read_all_events(data_dir)
        df = _latency_df(all_events)
        assert df is not None
        assert df["p50"].iloc[0] == 300  # median of [100,200,300,400,500]
        assert df["p95"].iloc[0] > 300
        assert df["count"].iloc[0] == 5

    def test_returns_none_without_latency_data(self, tmp_path: Path):
        events = [{"event_type": "feedback", "utility": 4}]
        data_dir = _write_events(tmp_path, events)
        all_events = _read_all_events(data_dir)
        df = _latency_df(all_events)
        assert df is None


class TestTierDistribution:
    def test_merges_across_events(self, tmp_path: Path):
        events = [
            _recall_event("2026-04-22", tier_dist={"A": 3}),
            _recall_event("2026-04-22", tier_dist={"B": 2}),
        ]
        data_dir = _write_events(tmp_path, events)
        all_events = _read_all_events(data_dir)
        df = _tier_distribution_df(all_events)
        assert df is not None
        tier_dict = dict(zip(df["tier"], df["count"]))
        assert tier_dict["A"] == 3
        assert tier_dict["B"] == 2


class TestUtilityDf:
    def test_computes_avg_utility(self, tmp_path: Path):
        events = [
            _feedback_event("2026-04-22", 3),
            _feedback_event("2026-04-22", 5),
        ]
        data_dir = _write_events(tmp_path, events)
        all_events = _read_all_events(data_dir)
        df = _utility_df(all_events)
        assert df is not None
        assert df["avg_utility"].iloc[0] == 4.0


class TestUnusedNotesSummary:
    def test_counts_un_cited_notes(self, tmp_path: Path):
        events = [
            _recall_event(
                "2026-04-22",
                notes=[
                    {"id": "n1", "tier": "A"},
                    {"id": "n2", "tier": "B"},
                    {"id": "n3", "tier": "B"},
                ],
                cited=["n1"],
            ),
        ]
        data_dir = _write_events(tmp_path, events)
        all_events = _read_all_events(data_dir)
        result = _unused_notes_summary(all_events)
        assert result == 2  # n2 and n3 were retrieved but not cited

    def test_returns_none_without_notes(self, tmp_path: Path):
        events = [_recall_event("2026-04-22")]
        data_dir = _write_events(tmp_path, events)
        all_events = _read_all_events(data_dir)
        result = _unused_notes_summary(all_events)
        assert result is None


class TestPercentile:
    def test_p50(self):
        assert _percentile([1, 2, 3, 4, 5], 50) == 3
        assert _percentile([10, 20], 50) == 15.0

    def test_p95(self):
        assert _percentile([100, 200, 300], 95) == 290.0

    def test_empty(self):
        assert _percentile([], 50) == 0
