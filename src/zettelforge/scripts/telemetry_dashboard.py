#!/usr/bin/env python3
"""Optional Streamlit telemetry dashboard for RFC-007 / US-005.

Reads telemetry JSONL files from ~/.amem/telemetry/ and displays:
- Query volume over time
- Latency trends (p50/p95)
- Tier distribution
- Utility scores over time
- Unused notes warning

    pip install streamlit pandas
    streamlit run src/zettelforge/scripts/telemetry_dashboard.py -- --data-dir ~/.amem/telemetry
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


def _read_all_events(data_dir: str) -> List[Dict[str, Any]]:
    """Read all events from daily telemetry JSONL files."""
    events: List[Dict[str, Any]] = []
    base = Path(data_dir)
    if not base.exists():
        return events
    for path in sorted(base.glob("telemetry_*.jsonl")):
        for line in path.read_text(encoding="utf-8").strip().split("\n"):
            if line.strip():
                date_str = path.stem.replace("telemetry_", "")
                record = json.loads(line)
                record["_date"] = date_str
                events.append(record)
    return events


def _query_volume_df(events: List[Dict[str, Any]]) -> Optional[pd.DataFrame]:
    """Aggregate query count by date."""
    queries: Counter = Counter()
    for e in events:
        if e.get("event_type") == "recall":
            queries[e.get("_date", "unknown")] += 1
    if not queries:
        return None
    df = pd.DataFrame(queries.items(), columns=["date", "queries"])
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


def _latency_df(events: List[Dict[str, Any]]) -> Optional[pd.DataFrame]:
    """Compute daily p50/p95 recall latency."""
    by_date: Dict[str, List[int]] = defaultdict(list)
    for e in events:
        if e.get("event_type") == "recall":
            dur = e.get("duration_ms")
            if dur is not None:
                by_date[e["_date"]].append(int(dur))

    if not by_date:
        return None

    rows = []
    for date, durations in sorted(by_date.items()):
        sorted_dur = sorted(durations)
        rows.append({
            "date": date,
            "p50": _percentile(sorted_dur, 50),
            "p95": _percentile(sorted_dur, 95),
            "mean": sum(durations) / len(durations),
            "count": len(durations),
        })

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


def _percentile(data: List[int], p: int) -> float:
    """Compute the p-th percentile of a list of ints."""
    if not data:
        return 0
    k = (len(data) - 1) * p / 100
    f = int(k)
    c = f + 1
    if c >= len(data):
        return float(data[f])
    return data[f] + (k - f) * (data[c] - data[f])


def _tier_distribution_df(events: List[Dict[str, Any]]) -> Optional[pd.DataFrame]:
    """Aggregate tier distribution across all events."""
    tier_dist: Counter = Counter()
    for e in events:
        td = e.get("tier_distribution")
        if td and isinstance(td, dict):
            tier_dist.update(td)
        for note in e.get("notes", []):
            tier = note.get("tier")
            if tier:
                tier_dist[tier] += 1

    if not tier_dist:
        return None

    df = pd.DataFrame(list(sorted(tier_dist.items())), columns=["tier", "count"])
    return df


def _utility_df(events: List[Dict[str, Any]]) -> Optional[pd.DataFrame]:
    """Aggregate daily average utility scores."""
    by_date: Dict[str, List[int]] = defaultdict(list)
    for e in events:
        if e.get("event_type") == "feedback":
            by_date[e["_date"]].append(int(e.get("utility", 0)))

    if not by_date:
        return None

    rows = []
    for date, utilities in sorted(by_date.items()):
        rows.append({
            "date": date,
            "avg_utility": sum(utilities) / len(utilities),
            "count": len(utilities),
        })

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


def _unused_notes_summary(events: List[Dict[str, Any]]) -> Optional[int]:
    """Compute total unused notes across all events."""
    total = 0
    for e in events:
        recalled = set()
        for note in e.get("notes", []):
            nid = note.get("id")
            if nid:
                recalled.add(nid)

        cited = set()
        for nid in e.get("cited_notes", []):
            cited.add(nid)

        total += len(recalled - cited)
    return total if total else None


def main(data_dir: str = str(Path.home() / ".amem" / "telemetry")) -> None:
    import streamlit as st

    st.set_page_config(page_title="ZettelForge Telemetry", layout="wide", page_icon="📊")
    st.title("ZettelForge Telemetry Dashboard")
    st.caption(f"Data source: `{data_dir}`")

    events = _read_all_events(data_dir)
    if not events:
        st.warning("No telemetry data found. Check your data directory or add telemetry data.")
        return

    st.subheader("Query Volume Over Time")
    qv_df = _query_volume_df(events)
    if qv_df is not None:
        st.line_chart(qv_df.set_index("date")["queries"])
    else:
        st.info("No recall events in telemetry data.")

    st.subheader("Latency Trends (p50/p95)")
    lat_df = _latency_df(events)
    if lat_df is not None:
        lat_df["date"] = lat_df["date"].dt.strftime("%Y-%m-%d")
        st.dataframe(lat_df, hide_index=True)
        # Use altair chart via st.line_chart with wide format
        chart_df = lat_df.set_index("date")[["p50", "p95", "mean"]]
        chart_df.index.name = ""
        st.line_chart(chart_df)
    else:
        st.info("No latency data available.")

    st.subheader("Tier Distribution")
    tier_df = _tier_distribution_df(events)
    if tier_df is not None:
        st.bar_chart(tier_df.set_index("tier"))
    else:
        st.info("No tier data available.")

    st.subheader("Utility Scores Over Time")
    util_df = _utility_df(events)
    if util_df is not None:
        st.line_chart(util_df.set_index("date")["avg_utility"])
    else:
        st.info("No feedback/utility data available.")

    unused = _unused_notes_summary(events)
    st.subheader("Unused Notes")
    if unused is not None and unused > 0:
        st.warning(f"**{unused}** notes were retrieved but never cited across all days. High unused rates may indicate retrieval noise.")
    elif unused is not None:
        st.success("All retrieved notes were cited. No unused notes detected.")
    else:
        st.info("No citation data available to assess unused notes.")


def cli() -> None:
    parser = argparse.ArgumentParser(description="Streamlit telemetry dashboard for ZettelForge")
    parser.add_argument("--data-dir", default=str(Path.home() / ".amem" / "telemetry"),
                        help="Directory containing telemetry JSONL files")
    args = parser.parse_args()
    main(args.data_dir)


# Module-level call for `streamlit run` compatibility
if __name__ == "__main__":
    main()
