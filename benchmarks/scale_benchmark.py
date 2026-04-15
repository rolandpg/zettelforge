#!/usr/bin/env python3
"""
Scale Benchmark — ZettelForge write/recall latency at 100 → 10K notes.

Measures per-note write latency (p50/p95/p99), per-query recall latency
(p50/p95/p99), ingestion rate, RSS memory usage, LanceDB table row counts,
and entity index size at each scale point.

Usage:
    python benchmarks/scale_benchmark.py                        # default 100,500,1000,2000
    python benchmarks/scale_benchmark.py --counts 100,500,1000  # custom list
    python benchmarks/scale_benchmark.py --max 5000             # up to 5K only
"""

import argparse
import json
import os
import random
import resource
import shutil
import statistics
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List

# Force JSONL backend before any zettelforge import
os.environ["ZETTELFORGE_BACKEND"] = "jsonl"

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from zettelforge import MemoryManager  # noqa: E402  (backend env must be set first)

# ---------------------------------------------------------------------------
# Synthetic CTI note corpus
# ---------------------------------------------------------------------------

ACTORS = [
    "APT28",
    "APT29",
    "APT41",
    "Lazarus",
    "Turla",
    "Sandworm",
    "Volt Typhoon",
    "Scattered Spider",
    "MuddyWater",
    "OilRig",
    "Charming Kitten",
    "Fancy Bear",
    "Cozy Bear",
    "UNC3944",
    "Kimsuky",
]

TOOLS = [
    "Cobalt Strike",
    "Mimikatz",
    "Metasploit",
    "BloodHound",
    "Empire",
    "Covenant",
    "Sliver",
    "Brute Ratel",
    "PowGoop",
    "Manuscrypt",
    "DROPBEAR",
    "Meterpreter",
    "SharpHound",
    "Rubeus",
    "CrackMapExec",
]

CVES = [f"CVE-2024-{i:04d}" for i in range(1, 500)]

SECTORS = [
    "defense contractors",
    "energy sector organizations",
    "financial institutions",
    "healthcare providers",
    "telecommunications companies",
    "government agencies",
    "critical infrastructure operators",
    "manufacturing plants",
    "logistics companies",
    "technology firms",
]

TECHNIQUES = [
    "spearphishing emails",
    "VPN appliance exploitation",
    "living-off-the-land binaries",
    "supply chain compromise",
    "credential stuffing",
    "MFA fatigue attacks",
    "SQL injection",
    "zero-day exploitation",
    "watering hole attacks",
    "drive-by compromise",
]

DOMAINS = ["threat_intel", "vulnerability", "incident_response", "malware_analysis"]


def generate_note(i: int) -> str:
    """Generate a realistic-ish CTI note for index i."""
    actor = random.choice(ACTORS)
    tool = random.choice(TOOLS)
    cve = random.choice(CVES)
    sector = random.choice(SECTORS)
    technique = random.choice(TECHNIQUES)
    secondary_actor = random.choice(ACTORS)
    secondary_tool = random.choice(TOOLS)

    templates = [
        (
            f"{actor} deployed {tool} exploiting {cve} targeting {sector}. "
            f"Initial access achieved via {technique}. Attribution confidence is high."
        ),
        (
            f"Incident #{i}: {actor} used {technique} to compromise {sector}. "
            f"Post-exploitation tooling included {tool} and {secondary_tool}. "
            f"Lateral movement observed using stolen credentials."
        ),
        (
            f"{cve} is being actively exploited by {actor} and {secondary_actor} "
            f"in campaigns against {sector}. Patch urgently to prevent {tool} deployment."
        ),
        (
            f"Malware analysis note {i}: {tool} sample linked to {actor} infrastructure. "
            f"C2 communication uses DNS over HTTPS. Targets {sector}. "
            f"Drops secondary payload via {secondary_tool}."
        ),
        (
            f"Threat actor {actor} updated their TTPs. Now using {cve} for initial access "
            f"and {tool} for persistence against {sector}. Previously relied on {technique}."
        ),
    ]
    return random.choice(templates)


# ---------------------------------------------------------------------------
# Percentile helpers
# ---------------------------------------------------------------------------


def percentile(data: List[float], p: float) -> float:
    """Return the p-th percentile of data (0-100). Returns 0.0 for empty lists."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    idx = (p / 100.0) * (len(sorted_data) - 1)
    lower = int(idx)
    upper = min(lower + 1, len(sorted_data) - 1)
    frac = idx - lower
    return sorted_data[lower] * (1.0 - frac) + sorted_data[upper] * frac


# ---------------------------------------------------------------------------
# LanceDB inspection helpers
# ---------------------------------------------------------------------------


def _count_lancedb_rows(lance_path: str) -> int:
    """Count total rows across all LanceDB tables in the given path."""
    try:
        import lancedb

        db = lancedb.connect(lance_path)
        total = 0
        list_fn = getattr(db, "list_tables", None) or db.table_names
        for name in list_fn():
            tbl = db.open_table(name)
            total += len(tbl)
        return total
    except Exception:
        return -1


def _count_entity_index(jsonl_path: str) -> int:
    """Count unique entity keys in the entity index JSON sidecar."""
    entity_index_path = Path(jsonl_path).parent / "entity_index.json"
    if not entity_index_path.exists():
        return -1
    try:
        with open(entity_index_path) as f:
            index = json.load(f)
        return len(index)
    except Exception:
        return -1


# ---------------------------------------------------------------------------
# Single scale-point benchmark
# ---------------------------------------------------------------------------

RECALL_QUERIES = [
    "What tools does APT28 use?",
    "Which threat actors exploit Cobalt Strike?",
    "CVE-2024-0042 exploitation details",
    "Lazarus Group financial sector attacks",
    "Living off the land techniques in critical infrastructure",
    "MFA fatigue attacks against enterprises",
    "BloodHound usage in lateral movement",
    "Sandworm targeting energy sector",
    "Supply chain compromise TTPs",
    "Volt Typhoon pre-positioning campaigns",
    "Credential dumping with Mimikatz",
    "APT41 malware families",
    "Ransomware deployment after initial access",
    "DNS over HTTPS C2 communication",
    "Spearphishing initial access vectors",
    "Turla backdoor persistence mechanisms",
    "Zero-day exploitation in VPN appliances",
    "North Korean cryptocurrency theft operations",
    "Iranian threat actors targeting telecom",
    "Scattered Spider social engineering",
]


def run_scale_point(
    note_count: int,
    rng_seed: int = 42,
) -> Dict:
    """Run a full benchmark at a single note count. Returns metrics dict."""
    random.seed(rng_seed)

    tmpdir = tempfile.mkdtemp(prefix=f"zf_bench_{note_count}_")
    jsonl_path = os.path.join(tmpdir, "notes.jsonl")
    lance_path = os.path.join(tmpdir, "vectordb")

    try:
        mm = MemoryManager(jsonl_path=jsonl_path, lance_path=lance_path)

        # ── Write phase ──────────────────────────────────────────────────────
        write_latencies_ms: List[float] = []
        ingest_start = time.perf_counter()

        for i in range(note_count):
            note_text = generate_note(i)
            domain = random.choice(DOMAINS)
            t0 = time.perf_counter()
            mm.remember(note_text, domain=domain)
            write_latencies_ms.append((time.perf_counter() - t0) * 1000.0)

        ingest_elapsed = time.perf_counter() - ingest_start
        ingestion_rate = note_count / ingest_elapsed if ingest_elapsed > 0 else 0.0

        # ── RSS memory after writes ──────────────────────────────────────────
        rss_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # Linux returns KB; macOS returns bytes
        if sys.platform == "darwin":
            rss_mb = rss_kb / (1024.0 * 1024.0)
        else:
            rss_mb = rss_kb / 1024.0

        # ── Recall phase ─────────────────────────────────────────────────────
        queries = RECALL_QUERIES[:20]
        recall_latencies_ms: List[float] = []

        for query in queries:
            t0 = time.perf_counter()
            mm.recall(query, k=5)
            recall_latencies_ms.append((time.perf_counter() - t0) * 1000.0)

        # ── Storage sizes ─────────────────────────────────────────────────────
        lancedb_rows = _count_lancedb_rows(lance_path)
        entity_count = _count_entity_index(jsonl_path)

        return {
            "note_count": note_count,
            "write_p50_ms": percentile(write_latencies_ms, 50),
            "write_p95_ms": percentile(write_latencies_ms, 95),
            "write_p99_ms": percentile(write_latencies_ms, 99),
            "recall_p50_ms": percentile(recall_latencies_ms, 50),
            "recall_p95_ms": percentile(recall_latencies_ms, 95),
            "recall_p99_ms": percentile(recall_latencies_ms, 99),
            "ingestion_rate_notes_per_sec": round(ingestion_rate, 2),
            "rss_mb": round(rss_mb, 1),
            "lancedb_rows": lancedb_rows,
            "entity_index_size": entity_count,
            "write_mean_ms": round(statistics.mean(write_latencies_ms), 2),
            "recall_mean_ms": round(statistics.mean(recall_latencies_ms), 2),
            "total_ingest_s": round(ingest_elapsed, 2),
        }
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Table printer
# ---------------------------------------------------------------------------

_COL_WIDTHS = {
    "Notes": 6,
    "Write p50": 10,
    "Write p95": 10,
    "Write p99": 10,
    "Recall p50": 11,
    "Recall p95": 11,
    "Notes/s": 9,
    "RSS MB": 8,
    "Entities": 10,
}

_HEADERS = list(_COL_WIDTHS.keys())


def _fmt(val: object, width: int) -> str:
    return str(val).rjust(width)


def print_table(results: List[Dict]) -> None:
    header = "  ".join(h.rjust(_COL_WIDTHS[h]) for h in _HEADERS)
    sep = "  ".join("-" * _COL_WIDTHS[h] for h in _HEADERS)
    print(header)
    print(sep)
    for r in results:
        row = [
            _fmt(r["note_count"], _COL_WIDTHS["Notes"]),
            _fmt(f"{r['write_p50_ms']:.1f}ms", _COL_WIDTHS["Write p50"]),
            _fmt(f"{r['write_p95_ms']:.1f}ms", _COL_WIDTHS["Write p95"]),
            _fmt(f"{r['write_p99_ms']:.1f}ms", _COL_WIDTHS["Write p99"]),
            _fmt(f"{r['recall_p50_ms']:.1f}ms", _COL_WIDTHS["Recall p50"]),
            _fmt(f"{r['recall_p95_ms']:.1f}ms", _COL_WIDTHS["Recall p95"]),
            _fmt(f"{r['ingestion_rate_notes_per_sec']:.1f}", _COL_WIDTHS["Notes/s"]),
            _fmt(r["rss_mb"], _COL_WIDTHS["RSS MB"]),
            _fmt(r["entity_index_size"] if r["entity_index_size"] >= 0 else "n/a", _COL_WIDTHS["Entities"]),
        ]
        print("  ".join(row))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

DEFAULT_COUNTS = [100, 500, 1000, 2000]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="ZettelForge scale benchmark — measures write/recall latency at increasing note counts.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--counts",
        type=str,
        default=None,
        metavar="N,N,...",
        help="Comma-separated list of note counts to benchmark (e.g. 100,500,1000).",
    )
    group.add_argument(
        "--max",
        type=int,
        default=None,
        metavar="N",
        help="Run all default scale points up to and including N.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(Path(__file__).parent / "scale_results.json"),
        metavar="PATH",
        help="Path to write JSON results (default: benchmarks/scale_results.json).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible synthetic data generation (default: 42).",
    )
    return parser.parse_args()


def resolve_counts(args: argparse.Namespace) -> List[int]:
    all_counts = [100, 500, 1000, 2000, 5000, 10000]

    if args.counts is not None:
        try:
            return sorted(int(x.strip()) for x in args.counts.split(",") if x.strip())
        except ValueError as exc:
            print(f"Error: --counts must be comma-separated integers. Got: {args.counts!r}")
            raise SystemExit(1) from exc

    if args.max is not None:
        filtered = [c for c in all_counts if c <= args.max]
        if not filtered:
            print(f"Error: --max {args.max} is less than the smallest scale point (100).")
            raise SystemExit(1)
        return filtered

    return DEFAULT_COUNTS


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    args = parse_args()
    counts = resolve_counts(args)

    print("ZettelForge Scale Benchmark")
    print("Backend : JSONL + LanceDB")
    print(f"Counts  : {counts}")
    print(f"Output  : {args.output}")
    print()

    results: List[Dict] = []

    for n in counts:
        print(f"  Running {n:>6} notes ... ", end="", flush=True)
        t_wall = time.perf_counter()
        metrics = run_scale_point(n, rng_seed=args.seed)
        elapsed = time.perf_counter() - t_wall
        results.append(metrics)
        print(f"done ({elapsed:.1f}s)")

    print()
    print_table(results)
    print()

    # Save JSON
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(
            {
                "benchmark": "scale_benchmark",
                "backend": "jsonl",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "counts": counts,
                "results": results,
            },
            f,
            indent=2,
        )
    print(f"Results saved to {output_path}")


if __name__ == "__main__":
    main()
