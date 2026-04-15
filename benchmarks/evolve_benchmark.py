#!/usr/bin/env python3
"""
Memory Evolution Quality Benchmark
====================================
Tests whether remember(evolve=True) makes correct ADD/UPDATE/DELETE/NOOP
decisions when note B is presented after note A has been stored.

Scoring:
  exact match          → 1.0
  reasonable alternate → 0.5  (e.g. UPDATE vs DELETE for contradiction cases)
  wrong                → 0.0

Usage:
  python benchmarks/evolve_benchmark.py --llm ollama --model qwen2.5:3b
  python benchmarks/evolve_benchmark.py --llm local
  python benchmarks/evolve_benchmark.py --quick          # 5 cases only
"""

import argparse
import json
import os
import statistics
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

# ── Version ──────────────────────────────────────────────────────────────────

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from zettelforge import MemoryManager, __version__

# ── Test Case Schema ──────────────────────────────────────────────────────────

CATEGORIES = ["UPDATE", "ADD", "NOOP", "DELETE"]


@dataclass
class EvolveCase:
    """A single benchmark test pair."""

    category: str  # UPDATE | ADD | NOOP | DELETE
    note_a: str  # Baseline note already in memory
    note_b: str  # Incoming note processed with evolve=True
    expected: str  # Expected status: "updated" | "added" | "noop" | "corrected"
    # Acceptable alternative decisions that score 0.5 rather than 0.0
    acceptable: list = field(default_factory=list)
    description: str = ""


# ── 30 Test Cases ─────────────────────────────────────────────────────────────

TEST_CASES: list[EvolveCase] = [
    # ── UPDATE: TTP / technique changes ──────────────────────────────────────
    EvolveCase(
        category="UPDATE",
        note_a="APT28 uses Cobalt Strike for command-and-control infrastructure.",
        note_b=(
            "APT28 has shifted from Cobalt Strike to the HeadLace backdoor "
            "for command-and-control operations as of late 2023."
        ),
        expected="updated",
        acceptable=["corrected"],
        description="TTP change: C2 tool replacement",
    ),
    EvolveCase(
        category="UPDATE",
        note_a="Lazarus Group primarily targets South Korean financial institutions.",
        note_b=(
            "Lazarus Group has expanded its targeting beyond South Korea to "
            "include cryptocurrency exchanges globally, as seen in 2024 campaigns."
        ),
        expected="updated",
        acceptable=["added"],
        description="Scope expansion of targeting",
    ),
    EvolveCase(
        category="UPDATE",
        note_a="CVE-2024-1111 is a critical remote code execution flaw affecting FortiGate 6.x.",
        note_b=(
            "CVE-2024-1111 has been confirmed to also affect FortiGate 7.0 firmware, "
            "expanding the vulnerable scope beyond the initially reported 6.x branch."
        ),
        expected="updated",
        acceptable=["added"],
        description="CVE scope expansion to newer firmware",
    ),
    EvolveCase(
        category="UPDATE",
        note_a="Server ALPHA at 10.0.1.50 is compromised and under active threat actor control.",
        note_b=(
            "Server ALPHA has been wiped, rebuilt from a clean image, and returned "
            "to production as of 2026-03-10. No persistence mechanisms were found."
        ),
        expected="updated",
        acceptable=["corrected"],
        description="Incident status change: compromised to remediated",
    ),
    EvolveCase(
        category="UPDATE",
        note_a="DarkSide ransomware group operates from Eastern Europe.",
        note_b=(
            "DarkSide ransomware group disbanded in May 2021 following the Colonial Pipeline "
            "attack and subsequent law enforcement pressure."
        ),
        expected="updated",
        acceptable=["corrected"],
        description="Threat actor operational status change",
    ),
    EvolveCase(
        category="UPDATE",
        note_a="Emotet is distributed primarily via malicious Word document email attachments.",
        note_b=(
            "Emotet evolved its delivery mechanism to use OneNote attachments and "
            "embedded macros after Microsoft disabled VBA macros by default in 2022."
        ),
        expected="updated",
        acceptable=["added"],
        description="Malware delivery method evolution",
    ),
    EvolveCase(
        category="UPDATE",
        note_a="CVE-2021-44228 (Log4Shell) has no known patch as of initial disclosure.",
        note_b=(
            "Apache released Log4j 2.17.1 patching CVE-2021-44228 (Log4Shell). "
            "Organizations should upgrade immediately."
        ),
        expected="updated",
        acceptable=["corrected"],
        description="Patch availability update for CVE",
    ),
    EvolveCase(
        category="UPDATE",
        note_a="Threat actor TA505 uses FlawedAmmyy RAT as primary post-exploitation tool.",
        note_b=(
            "TA505 has pivoted away from FlawedAmmyy RAT toward Clop ransomware "
            "deployment in recent intrusions observed in Q1 2024."
        ),
        expected="updated",
        acceptable=["corrected"],
        description="Threat actor tooling pivot",
    ),
    EvolveCase(
        category="UPDATE",
        note_a="SolarWinds Orion platform was used as an attack vector in the SUNBURST campaign.",
        note_b=(
            "Post-incident analysis confirmed that the SolarWinds SUNBURST "
            "compromise also affected the SolarWinds Serv-U FTP server, expanding "
            "the known attack surface."
        ),
        expected="updated",
        acceptable=["added"],
        description="Attack surface scope expansion",
    ),
    EvolveCase(
        category="UPDATE",
        note_a="Cobalt Strike version 4.5 is widely used by threat actors.",
        note_b=(
            "Cobalt Strike 4.9 introduced enhanced OPSEC defaults and beaconing "
            "obfuscation, replacing 4.5 as the most commonly observed version "
            "in enterprise intrusions."
        ),
        expected="updated",
        acceptable=["added"],
        description="Software version currency update",
    ),
    # ── ADD: Genuinely new, unrelated information ─────────────────────────────
    EvolveCase(
        category="ADD",
        note_a="APT28 uses Cobalt Strike for command-and-control infrastructure.",
        note_b=(
            "Fortinet released a critical patch for CVE-2024-1111 on March 15, 2024. "
            "All FortiGate administrators should apply the update immediately."
        ),
        expected="added",
        description="Unrelated new fact: vendor patch release",
    ),
    EvolveCase(
        category="ADD",
        note_a="Lazarus Group targets cryptocurrency exchanges to fund North Korean operations.",
        note_b=(
            "CISA issued advisory AA26-078A on March 19, 2026 regarding DTrack malware "
            "activity targeting critical infrastructure sectors."
        ),
        expected="added",
        description="New CISA advisory: distinct subject matter",
    ),
    EvolveCase(
        category="ADD",
        note_a="Ransomware gangs increasingly use double extortion tactics.",
        note_b=(
            "A new threat actor cluster tracked as UNC5325 was observed exploiting "
            "Ivanti Connect Secure zero-days in January 2024."
        ),
        expected="added",
        description="New threat actor cluster: no overlap with baseline",
    ),
    EvolveCase(
        category="ADD",
        note_a="Phishing campaigns targeting executives use lookalike domains.",
        note_b=(
            "MITRE ATT&CK v15 was released on April 23, 2024, adding 14 new "
            "techniques and updating 110 existing entries."
        ),
        expected="added",
        description="New framework release: unrelated to phishing",
    ),
    EvolveCase(
        category="ADD",
        note_a="CVE-2024-3094 is a supply chain backdoor inserted into XZ Utils 5.6.0.",
        note_b=(
            "The Python Software Foundation released Python 3.13.0 on October 7, 2024 "
            "with significant performance improvements via JIT compilation."
        ),
        expected="added",
        description="Completely different domain: Python release vs. CVE",
    ),
    EvolveCase(
        category="ADD",
        note_a="BlackCat ransomware is written in Rust for cross-platform capability.",
        note_b=(
            "The FBI disrupted the BlackCat/ALPHV ransomware group infrastructure "
            "in December 2023 and seized their dark web leak site."
        ),
        expected="added",
        acceptable=["updated"],
        description="New law enforcement action (may relate to BlackCat)",
    ),
    EvolveCase(
        category="ADD",
        note_a="Midnight Blizzard used password spray attacks against Microsoft in January 2024.",
        note_b=(
            "The SEC adopted new cybersecurity disclosure rules requiring public companies "
            "to report material breaches within four business days."
        ),
        expected="added",
        description="New regulatory rule: unrelated to Midnight Blizzard",
    ),
    EvolveCase(
        category="ADD",
        note_a="Volt Typhoon pre-positions in US critical infrastructure for potential disruption.",
        note_b=(
            "Wiz Research discovered a new cloud misconfiguration pattern affecting "
            "Azure Blob Storage containers with public access enabled."
        ),
        expected="added",
        description="New cloud research: distinct from Volt Typhoon activity",
    ),
    # ── NOOP: Note B is a restatement / known alias of note A ─────────────────
    EvolveCase(
        category="NOOP",
        note_a="APT28 is a Russian state-sponsored threat actor attributed to the GRU.",
        note_b=(
            "APT28, also known as Fancy Bear, is a Russian cyber espionage group "
            "attributed to Russian military intelligence (GRU)."
        ),
        expected="noop",
        acceptable=["updated"],
        description="Same fact with alias added: Fancy Bear == APT28",
    ),
    EvolveCase(
        category="NOOP",
        note_a=(
            "CVE-2024-3094 is a critical backdoor inserted into the XZ Utils "
            "compression library versions 5.6.0 and 5.6.1 by a malicious maintainer."
        ),
        note_b=(
            "A backdoor was discovered in XZ Utils (CVE-2024-3094) affecting "
            "versions 5.6.0 and 5.6.1, introduced by maintainer Jia Tan."
        ),
        expected="noop",
        acceptable=["updated"],
        description="Rephrased with minor added detail: same core fact",
    ),
    EvolveCase(
        category="NOOP",
        note_a="WannaCry ransomware exploits the EternalBlue SMB vulnerability (MS17-010).",
        note_b=(
            "WannaCry worm uses EternalBlue (MS17-010), a vulnerability in Windows SMB, "
            "to propagate across networks."
        ),
        expected="noop",
        acceptable=["updated"],
        description="Rephrased duplicate: same technical claim",
    ),
    EvolveCase(
        category="NOOP",
        note_a="Conti ransomware gang operates from Russia and targets healthcare organizations.",
        note_b="The Conti group, a Russian ransomware operation, is known to attack healthcare.",
        expected="noop",
        acceptable=["updated"],
        description="Shortened restatement of existing fact",
    ),
    EvolveCase(
        category="NOOP",
        note_a=(
            "The MITRE ATT&CK framework catalogs adversary tactics, techniques, "
            "and procedures (TTPs) for enterprise environments."
        ),
        note_b=(
            "MITRE ATT&CK is a knowledge base of adversary TTPs used for threat "
            "modeling and detection engineering in enterprise security."
        ),
        expected="noop",
        acceptable=["updated"],
        description="Semantic paraphrase: same framework description",
    ),
    EvolveCase(
        category="NOOP",
        note_a="Cobalt Strike is a commercial red team tool frequently misused by threat actors.",
        note_b=(
            "Cobalt Strike, originally designed for penetration testing, is widely "
            "abused by cybercriminals and nation-state actors as attack infrastructure."
        ),
        expected="noop",
        acceptable=["updated"],
        description="Expanded phrasing of same well-known fact",
    ),
    # ── DELETE / Correct: Note B contradicts note A ────────────────────────────
    EvolveCase(
        category="DELETE",
        note_a="The 2023 MOVEit data breach was attributed to APT28.",
        note_b=(
            "Updated attribution analysis: the MOVEit data breach was conducted by "
            "the Cl0p ransomware group (TA505), not APT28. Earlier attribution was incorrect."
        ),
        expected="corrected",
        acceptable=["updated"],
        description="Attribution correction: wrong actor replaced",
    ),
    EvolveCase(
        category="DELETE",
        note_a="CVE-2024-5555 has a CVSS score of 4.3 (Medium severity).",
        note_b=(
            "NIST revised the CVSS score for CVE-2024-5555 from 4.3 to 9.8 (Critical) "
            "after re-analysis confirmed unauthenticated remote code execution."
        ),
        expected="corrected",
        acceptable=["updated"],
        description="Severity score correction from medium to critical",
    ),
    EvolveCase(
        category="DELETE",
        note_a="Midnight Blizzard (NOBELIUM) is attributed to Chinese intelligence services.",
        note_b=(
            "Correction: Midnight Blizzard (NOBELIUM) is attributed to Russia's SVR "
            "foreign intelligence service, not China. Prior attribution was erroneous."
        ),
        expected="corrected",
        acceptable=["updated"],
        description="Nation-state attribution correction",
    ),
    EvolveCase(
        category="DELETE",
        note_a=(
            "The Log4Shell vulnerability (CVE-2021-44228) requires authentication "
            "to exploit in default configurations."
        ),
        note_b=(
            "Correction: CVE-2021-44228 (Log4Shell) is unauthenticated and exploitable "
            "in default configurations with no prior access required. "
            "Prior statement was factually wrong."
        ),
        expected="corrected",
        acceptable=["updated"],
        description="Technical error correction: auth requirement",
    ),
    EvolveCase(
        category="DELETE",
        note_a="Sandworm is a financially motivated criminal group based in Ukraine.",
        note_b=(
            "Sandworm is a Russian GRU-attributed threat actor (Unit 74455) focused on "
            "destructive cyber operations, not financially motivated and not Ukrainian. "
            "The prior note contained multiple factual errors."
        ),
        expected="corrected",
        acceptable=["updated"],
        description="Multiple attribution errors corrected",
    ),
    EvolveCase(
        category="DELETE",
        note_a="The NotPetya attack in 2017 was ransomware intended to generate revenue.",
        note_b=(
            "NotPetya was a destructive wiper disguised as ransomware with no working "
            "decryption mechanism. It was designed to destroy data, not generate ransom."
        ),
        expected="corrected",
        acceptable=["updated"],
        description="Malware classification correction: wiper vs ransomware",
    ),
]


# ── Status Normalisation ──────────────────────────────────────────────────────

# evolve=True returns statuses from remember_with_extraction / updater.apply
# Map the set of possible returned strings to canonical expected values
_STATUS_ALIASES: dict[str, str] = {
    "added": "added",
    "updated": "updated",
    "corrected": "corrected",
    "noop": "noop",
    # Direct path fallback returns "created" — treat as "added" for scoring
    "created": "added",
}


def normalise_status(raw: Optional[str]) -> str:
    """Normalise a raw status string to canonical form."""
    if raw is None:
        return "unknown"
    return _STATUS_ALIASES.get(raw.lower().strip(), raw.lower().strip())


# ── Scoring ───────────────────────────────────────────────────────────────────


def score_result(actual: str, case: EvolveCase) -> float:
    """Return 1.0, 0.5, or 0.0 for a prediction against expected."""
    if actual == case.expected:
        return 1.0
    if actual in case.acceptable:
        return 0.5
    return 0.0


# ── Benchmark Runner ──────────────────────────────────────────────────────────


def run_single_case(
    case: EvolveCase,
    case_index: int,
) -> dict:
    """
    Run one test case in an isolated temp directory.

    Returns a result dict with actual status, score, latency, and debug info.
    """
    tmpdir = tempfile.mkdtemp(prefix=f"evolve_bench_{case_index}_")

    start = time.perf_counter()
    actual_status = "unknown"
    error_msg = None

    try:
        mm = MemoryManager(
            jsonl_path=f"{tmpdir}/notes.jsonl",
            lance_path=f"{tmpdir}/vectordb",
        )

        # Phase 1: store baseline note WITHOUT evolve
        mm.remember(
            content=case.note_a,
            source_type="benchmark",
            source_ref=f"evolve_bench:{case_index}:baseline",
            domain="cti",
            evolve=False,
        )

        # Phase 2: present note_b WITH evolve=True — this is what we're testing
        _note, raw_status = mm.remember(
            content=case.note_b,
            source_type="benchmark",
            source_ref=f"evolve_bench:{case_index}:candidate",
            domain="cti",
            evolve=True,
        )

        actual_status = normalise_status(raw_status)

    except Exception as exc:
        error_msg = str(exc)
        actual_status = "error"

    latency_ms = (time.perf_counter() - start) * 1000
    sc = score_result(actual_status, case)

    return {
        "index": case_index,
        "category": case.category,
        "description": case.description,
        "note_a": case.note_a[:120],
        "note_b": case.note_b[:120],
        "expected": case.expected,
        "actual": actual_status,
        "score": sc,
        "latency_ms": round(latency_ms, 1),
        "error": error_msg,
    }


def run_benchmark(
    cases: list[EvolveCase],
    quick: bool = False,
) -> dict:
    """Execute all test cases and return structured results."""
    if quick:
        # One case from each category for a fast sanity check
        selected: list[EvolveCase] = []
        seen: set[str] = set()
        for c in cases:
            if c.category not in seen:
                selected.append(c)
                seen.add(c.category)
            if len(selected) == 4:
                break
        # Add one more for coverage
        for c in cases:
            if c not in selected:
                selected.append(c)
                break
        cases = selected
        print(f"[quick mode] Running {len(cases)} cases (one per category + 1).")
    else:
        print(f"Running {len(cases)} cases across {len(CATEGORIES)} categories.")

    results = []
    for i, case in enumerate(cases):
        print(f"  [{i + 1:>2}/{len(cases)}] {case.category:<8} {case.description[:55]}", end="", flush=True)
        result = run_single_case(case, i)
        mark = {1.0: "PASS", 0.5: "HALF", 0.0: "FAIL"}.get(result["score"], "ERR ")
        if result["actual"] == "error":
            mark = "ERR "
        print(f"  [{mark}]  actual={result['actual']:<12} expected={result['expected']:<12} ({result['latency_ms']:.0f}ms)")
        results.append(result)

    return results


# ── Reporting ─────────────────────────────────────────────────────────────────


def print_report(results: list[dict]) -> dict:
    """Print table and return summary dict."""
    by_category: dict[str, list] = {c: [] for c in CATEGORIES}
    for r in results:
        by_category.setdefault(r["category"], []).append(r)

    print()
    print("=" * 72)
    print(
        f"{'Category':<12} {'Exact%':>8} {'AvgScore':>9} "
        f"{'p50 Lat':>10} {'Pass':>5} {'Half':>5} {'Fail':>5} {'N':>5}"
    )
    print("-" * 72)

    all_scores: list[float] = []
    all_latencies: list[float] = []

    for cat in CATEGORIES:
        cat_results = by_category.get(cat, [])
        if not cat_results:
            print(f"{cat:<12} {'--':>8} {'--':>9} {'--':>10} {'--':>5} {'--':>5} {'--':>5} {'0':>5}")
            continue

        scores = [r["score"] for r in cat_results]
        latencies = [r["latency_ms"] for r in cat_results]

        exact = sum(1 for s in scores if s == 1.0)
        half = sum(1 for s in scores if s == 0.5)
        fail = sum(1 for s in scores if s == 0.0)
        exact_pct = exact / len(scores) * 100
        avg_score = statistics.mean(scores)
        p50_lat = statistics.median(latencies)

        print(
            f"{cat:<12} {exact_pct:>7.1f}% {avg_score:>9.2f} "
            f"{p50_lat:>8.0f}ms {exact:>5} {half:>5} {fail:>5} {len(scores):>5}"
        )

        all_scores.extend(scores)
        all_latencies.extend(latencies)

    print("-" * 72)

    overall: dict = {}
    if all_scores:
        oa = sum(1 for s in all_scores if s == 1.0) / len(all_scores) * 100
        avg = statistics.mean(all_scores)
        p50 = statistics.median(all_latencies)
        p95 = sorted(all_latencies)[max(0, int(len(all_latencies) * 0.95) - 1)]
        print(
            f"{'OVERALL':<12} {oa:>7.1f}% {avg:>9.2f} "
            f"{p50:>8.0f}ms {'':>5} {'':>5} {'':>5} {len(all_scores):>5}"
        )
        overall = {
            "exact_accuracy_pct": round(oa, 2),
            "avg_score": round(avg, 4),
            "p50_latency_ms": round(p50, 1),
            "p95_latency_ms": round(p95, 1),
            "n": len(all_scores),
        }

    print("=" * 72)
    return overall


# ── Entry Point ───────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ZettelForge evolve=True quality benchmark"
    )
    parser.add_argument(
        "--llm",
        choices=["local", "ollama"],
        default="local",
        help="LLM backend for evolve decisions (default: local)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help=(
            "Model name/repo. For local: HuggingFace repo ID. "
            "For ollama: model tag (e.g. qwen2.5:3b)."
        ),
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run only 5 cases (one per category + 1) for a fast sanity check",
    )
    parser.add_argument(
        "--output",
        default=str(Path(__file__).parent / "evolve_results.json"),
        help="Path to save JSON results (default: benchmarks/evolve_results.json)",
    )
    args = parser.parse_args()

    # ── Environment setup ─────────────────────────────────────────────────────
    os.environ["ZETTELFORGE_BACKEND"] = "jsonl"
    os.environ["ZETTELFORGE_LLM_PROVIDER"] = args.llm

    if args.model:
        if args.llm == "local":
            os.environ["ZETTELFORGE_LLM_MODEL"] = args.model
        else:
            os.environ["ZETTELFORGE_OLLAMA_MODEL"] = args.model

    # ── Probe LLM availability ────────────────────────────────────────────────
    print(f"ZettelForge evolve=True Benchmark  (v{__version__})")
    print(f"LLM backend : {args.llm}")
    print(f"Model       : {args.model or '(default)'}")
    print(f"Mode        : {'quick (5 cases)' if args.quick else f'full ({len(TEST_CASES)} cases)'}")
    print()

    try:
        from zettelforge.llm_client import generate

        probe = generate("Respond with only the word: READY", max_tokens=10, temperature=0.0)
        if not probe:
            print("WARNING: LLM probe returned empty response. evolve=True may default to ADD.")
        else:
            print(f"LLM probe   : OK (response snippet: {probe[:40]!r})")
    except Exception as exc:
        print(f"WARNING: LLM unavailable ({exc}). evolve=True will default to ADD for all cases.")
        print("         Results will be biased. Consider --llm ollama with a running Ollama server.")

    print()

    # ── Run ───────────────────────────────────────────────────────────────────
    results = run_benchmark(TEST_CASES, quick=args.quick)

    # ── Report ────────────────────────────────────────────────────────────────
    overall = print_report(results)

    # ── Failures detail ───────────────────────────────────────────────────────
    failures = [r for r in results if r["score"] < 1.0]
    if failures:
        print(f"\nNon-perfect decisions ({len(failures)}):")
        for r in failures:
            mark = "HALF" if r["score"] == 0.5 else "FAIL"
            err = f"  ERROR: {r['error']}" if r["error"] else ""
            print(f"  [{mark}] #{r['index']:>2} {r['category']:<8} "
                  f"expected={r['expected']:<12} actual={r['actual']}{err}")
            print(f"         A: {r['note_a'][:80]}")
            print(f"         B: {r['note_b'][:80]}")

    # ── Persist results ───────────────────────────────────────────────────────
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "meta": {
            "date": datetime.now().isoformat(),
            "version": f"zettelforge-{__version__}",
            "llm_backend": args.llm,
            "model": args.model or "default",
            "mode": "quick" if args.quick else "full",
            "n_cases": len(results),
        },
        "overall": overall,
        "by_category": {
            cat: {
                "exact_accuracy_pct": (
                    sum(1 for r in [x for x in results if x["category"] == cat] if r["score"] == 1.0)
                    / max(1, sum(1 for r in results if r["category"] == cat))
                    * 100
                ),
                "avg_score": (
                    statistics.mean([r["score"] for r in results if r["category"] == cat])
                    if any(r["category"] == cat for r in results)
                    else 0.0
                ),
                "n": sum(1 for r in results if r["category"] == cat),
            }
            for cat in CATEGORIES
        },
        "cases": results,
    }

    with open(output_path, "w") as fh:
        json.dump(payload, fh, indent=2)

    print(f"\nResults saved: {output_path}")


if __name__ == "__main__":
    main()
