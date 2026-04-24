"""Tests for human_eval_sampler.py (RFC-007 / US-004)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from zettelforge.scripts.human_eval_sampler import (
    _build_rubric_template,
    _format_briefing,
    _read_telemetry,
    main,
)


def _synthesis_event(
    query: str = "APT28 infrastructure",
    confidence: float = 0.8,
    sources: int = 5,
    latency: int = 2500,
    cited: list[str] | None = None,
    actor: str = "vigil",
    ts: str = "2026-04-22T08:15:00",
) -> Dict[str, Any]:
    return {
        "event_type": "synthesis",
        "query": query,
        "confidence": confidence,
        "result_count": sources,
        "duration_ms": latency,
        "cited_notes": cited or [],
        "actor": actor,
        "ts": ts,
    }


def _write_telemetry(tmp_path: Path, events: list[Dict[str, Any]]) -> str:
    """Write events into telemetry JSONL files."""
    date_groups: dict[str, list[str]] = {}
    for ev in events:
        ts = ev.get("ts", ev.get("timestamp", ""))
        if ts:
            date = ts[:10]  # YYYY-MM-DD
        else:
            date = "2026-04-22"
        date_groups.setdefault(date, []).append(json.dumps(ev))

    for date, lines in date_groups.items():
        (tmp_path / f"telemetry_{date}.jsonl").write_text("\n".join(lines) + "\n")

    return str(tmp_path)


class TestReadTelemetry:
    def test_returns_synthesis_only(self, tmp_path: Path):
        events = [
            _synthesis_event("q1"),
            {"event_type": "recall", "query": "q1"},
            _synthesis_event("q2"),
        ]
        data_dir = _write_telemetry(tmp_path, events)
        result = _read_telemetry(data_dir)
        assert len(result) == 2
        assert all(e["event_type"] == "synthesis" for e in result)

    def test_empty_when_no_files(self, tmp_path: Path):
        result = _read_telemetry(str(tmp_path))
        assert result == []


class TestFormatBriefing:
    def test_includes_key_fields(self):
        ev = _synthesis_event("test query", confidence=0.75, sources=3, cited=["n1", "n2"])
        formatted = _format_briefing(ev, 1)
        assert "### Briefing #1" in formatted
        assert "test query" in formatted
        assert "3" in formatted
        assert "0.75" in formatted
        assert "n1" in formatted

    def test_defaults_for_missing_fields(self):
        ev = {"event_type": "synthesis"}
        formatted = _format_briefing(ev, 5)
        assert "Briefing #5" in formatted
        assert "(no query text)" in formatted


class TestRubricTemplate:
    def test_contains_all_six_criteria(self):
        template = _build_rubric_template()
        for name in [
            "Recall relevance",
            "Synthesis value",
            "Critical notes missing",
            "Unsupported claims",
            "Latency perception",
            "Overall trust",
        ]:
            assert name in template


class TestMain:
    def test_no_events_returns_empty(self, tmp_path: Path):
        data_dir = _write_telemetry(tmp_path, [])
        result = main(dates_dir=data_dir, count=10)
        assert result == ""

    def test_selects_subset(self, tmp_path: Path):
        events = [_synthesis_event(f"query-{i}") for i in range(50)]
        data_dir = _write_telemetry(tmp_path, events)
        result = main(dates_dir=data_dir, count=5)
        # Should contain exactly 5 briefings
        briefing_count = result.count("### Briefing #")
        assert briefing_count == 5

    def test_single_date_mode(self, tmp_path: Path):
        events = [_synthesis_event(f"q{i}") for i in range(10)]
        data_dir = _write_telemetry(tmp_path, events)
        result = main(dates_dir=data_dir, date_str="2026-04-22", count=3)
        assert result.count("### Briefing #") == 3

    def test_missing_date_prints_error(self, tmp_path: Path):
        result = main(dates_dir=str(tmp_path), date_str="2099-01-01", count=5)
        assert result == ""
