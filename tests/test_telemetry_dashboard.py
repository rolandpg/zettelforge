"""Tests for the telemetry dashboard computations (RFC-007 / US-005).

Covers the pure data-computation helpers (daily_volume,
latency_percentiles, tier_distribution, utility_trend, unused_notes).
The Streamlit render() entrypoint is GUI plumbing and imports streamlit
lazily; it's not unit-tested here.

Requires pandas (dashboard's only hard dep at module load). Skips if
pandas is missing so CI images without it don't fail this file.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("pandas")

import pandas as pd  # noqa: E402

from zettelforge.scripts.telemetry_dashboard import (  # noqa: E402
    daily_volume,
    latency_percentiles,
    load_events,
    tier_distribution,
    to_dataframe,
    unused_notes,
    utility_trend,
)

# ── Fixtures ─────────────────────────────────────────────────────────────


def _mixed_events() -> list:
    """A mixed bag covering every event type the dashboard handles."""
    return [
        # Two recalls on 2026-04-22, one on 2026-04-23
        {
            "event_type": "recall",
            "timestamp": 1745452800.0,  # 2026-04-23 00:00:00 UTC-ish
            "query_id": "q1",
            "result_count": 3,
            "duration_ms": 100,
            "tier_distribution": {"A": 2, "B": 1},
            "notes": [
                {"id": "n1", "rank": 0, "tier": "A"},
                {"id": "n2", "rank": 1, "tier": "A"},
                {"id": "n3", "rank": 2, "tier": "B"},
            ],
        },
        {
            "event_type": "recall",
            "timestamp": 1745366400.0,  # 2026-04-22
            "query_id": "q2",
            "result_count": 2,
            "duration_ms": 200,
            "tier_distribution": {"A": 1, "C": 1},
            "notes": [
                {"id": "n4", "rank": 0, "tier": "A"},
                {"id": "n5", "rank": 1, "tier": "C"},
            ],
        },
        {
            "event_type": "recall",
            "timestamp": 1745366400.0,  # 2026-04-22
            "query_id": "q3",
            "result_count": 1,
            "duration_ms": 500,
        },
        # Syntheses
        {
            "event_type": "synthesis",
            "timestamp": 1745452800.0,
            "query_id": "q1",
            "duration_ms": 2000,
            "confidence": 0.9,
        },
        {
            "event_type": "synthesis",
            "timestamp": 1745366400.0,
            "query_id": "q2",
            "duration_ms": 3000,
            "confidence": 0.75,
        },
        # Feedback: n1 and n4 get utility=4 (cited), n2 and n5 get utility=2
        {"event_type": "feedback", "timestamp": 1745452800.0, "note_id": "n1", "utility": 4},
        {"event_type": "feedback", "timestamp": 1745452800.0, "note_id": "n2", "utility": 2},
        {"event_type": "feedback", "timestamp": 1745366400.0, "note_id": "n4", "utility": 4},
        {"event_type": "feedback", "timestamp": 1745366400.0, "note_id": "n5", "utility": 2},
    ]


@pytest.fixture
def df() -> pd.DataFrame:
    return to_dataframe(_mixed_events())


# ── load_events ──────────────────────────────────────────────────────────


class TestLoadEvents:
    def test_missing_dir_returns_empty(self, tmp_path: Path) -> None:
        assert load_events(tmp_path / "nope") == []

    def test_loads_multiple_days(self, tmp_path: Path) -> None:
        (tmp_path / "telemetry_2026-04-22.jsonl").write_text(
            json.dumps({"event_type": "recall", "query_id": "a", "timestamp": 1.0}) + "\n"
        )
        (tmp_path / "telemetry_2026-04-23.jsonl").write_text(
            json.dumps({"event_type": "synthesis", "query_id": "b", "timestamp": 2.0}) + "\n"
        )
        events = load_events(tmp_path)
        assert {e["event_type"] for e in events} == {"recall", "synthesis"}

    def test_tolerates_corrupt_lines(self, tmp_path: Path) -> None:
        path = tmp_path / "telemetry_2026-04-23.jsonl"
        path.write_text(
            json.dumps({"event_type": "recall", "query_id": "good", "timestamp": 1.0}) + "\n"
            + "{malformed\n"
        )
        events = load_events(tmp_path)
        assert len(events) == 1
        assert events[0]["query_id"] == "good"


# ── daily_volume ─────────────────────────────────────────────────────────


class TestDailyVolume:
    def test_counts_per_day_per_type(self, df: pd.DataFrame) -> None:
        volume = daily_volume(df)
        lookup = {(r["date"], r["event_type"]): r["count"] for _, r in volume.iterrows()}
        # Dates derived from timestamps 1745452800 and 1745366400
        # (actual date-string depends on local timezone; assert structure, not values)
        recall_counts = {k: v for k, v in lookup.items() if k[1] == "recall"}
        synth_counts = {k: v for k, v in lookup.items() if k[1] == "synthesis"}
        assert sum(recall_counts.values()) == 3
        assert sum(synth_counts.values()) == 2

    def test_excludes_feedback_events(self, df: pd.DataFrame) -> None:
        volume = daily_volume(df)
        assert "feedback" not in set(volume["event_type"])

    def test_empty_df_returns_empty(self) -> None:
        empty = pd.DataFrame(columns=["event_type", "date", "duration_ms"])
        volume = daily_volume(empty)
        assert volume.empty


# ── latency_percentiles ──────────────────────────────────────────────────


class TestLatencyPercentiles:
    def test_recall_percentiles(self, df: pd.DataFrame) -> None:
        stats = latency_percentiles(df, "recall")
        # Recalls: 100, 200, 500 → p50 = 200, p95 ≈ 470, max = 500
        assert stats["p50"] == 200.0
        assert stats["max"] == 500.0
        assert stats["p95"] > stats["p50"]

    def test_synthesis_percentiles(self, df: pd.DataFrame) -> None:
        stats = latency_percentiles(df, "synthesis")
        assert stats["p50"] == 2500.0  # median of [2000, 3000]
        assert stats["max"] == 3000.0

    def test_no_events_returns_zeros(self, df: pd.DataFrame) -> None:
        stats = latency_percentiles(df, "nonexistent")
        assert stats == {"p50": 0.0, "p95": 0.0, "max": 0.0}


# ── tier_distribution ────────────────────────────────────────────────────


class TestTierDistribution:
    def test_sums_across_events(self, df: pd.DataFrame) -> None:
        tiers = tier_distribution(df)
        # Event 1: A=2, B=1; Event 2: A=1, C=1
        assert tiers == {"A": 3, "B": 1, "C": 1}

    def test_ignores_missing_tier_distribution(self) -> None:
        # One recall without tier_distribution (INFO mode) should not crash.
        df = to_dataframe(
            [
                {"event_type": "recall", "timestamp": 1.0, "tier_distribution": {"A": 2}},
                {"event_type": "recall", "timestamp": 1.0},  # INFO mode — no tier dist
            ]
        )
        assert tier_distribution(df) == {"A": 2}


# ── utility_trend ────────────────────────────────────────────────────────


class TestUtilityTrend:
    def test_mean_utility_per_day(self, df: pd.DataFrame) -> None:
        trend = utility_trend(df)
        # Mean per day should be 3 (4 + 2) / 2 on each day
        assert not trend.empty
        assert all(trend["mean_utility"] == 3.0)

    def test_no_feedback_returns_empty(self) -> None:
        df = to_dataframe([{"event_type": "recall", "timestamp": 1.0}])
        assert utility_trend(df).empty


# ── unused_notes ─────────────────────────────────────────────────────────


class TestUnusedNotes:
    def test_finds_notes_retrieved_but_never_cited(self, df: pd.DataFrame) -> None:
        unused = unused_notes(df)
        # n1,n4 cited (utility=4); n2,n5 uncited (utility=2); n3 retrieved but no feedback at all
        assert set(unused) == {"n2", "n3", "n5"}

    def test_all_cited_returns_empty(self) -> None:
        df = to_dataframe(
            [
                {
                    "event_type": "recall",
                    "timestamp": 1.0,
                    "notes": [{"id": "n1"}],
                },
                {
                    "event_type": "feedback",
                    "timestamp": 1.0,
                    "note_id": "n1",
                    "utility": 5,
                },
            ]
        )
        assert unused_notes(df) == []

    def test_empty_df_returns_empty(self) -> None:
        df = to_dataframe([])
        assert unused_notes(df) == []
