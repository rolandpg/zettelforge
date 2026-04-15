#!/usr/bin/env python3
"""
OpenCTI Live Benchmark — Real CTI Data from Production OpenCTI Instance
========================================================================
Pulls real threat intelligence from a running OpenCTI instance via pycti,
ingests into ZettelForge, then evaluates retrieval against OpenCTI's
structured entity relationships as ground truth.

This is a demo-ready benchmark that shows ZettelForge + OpenCTI integration
working end-to-end on real data.

Requires:
  - Running OpenCTI instance (http://localhost:8080 by default)
  - OPENCTI_TOKEN environment variable or --token flag
  - pycti: pip install pycti
  - ZettelForge Enterprise edition for full sync features

Usage:
  python benchmarks/opencti_benchmark.py                          # Quick demo
  python benchmarks/opencti_benchmark.py --reports 50 --queries 30  # Full run
  python benchmarks/opencti_benchmark.py --token YOUR_TOKEN       # Custom token
  python benchmarks/opencti_benchmark.py --url http://opencti:8080  # Remote instance
"""

import argparse
import json
import os
import statistics
import tempfile
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from zettelforge import MemoryManager, __version__


def get_opencti_client(url: str, token: str):
    """Initialize pycti client."""
    from pycti import OpenCTIApiClient

    return OpenCTIApiClient(url, token, log_level="WARNING")


# ── Data Pulling ────────────────────────────────────────────────────────────


def pull_reports_with_entities(api, limit: int = 20) -> List[Dict]:
    """Pull reports from OpenCTI with their linked entities."""
    reports = api.report.list(first=limit, orderBy="created_at", orderMode="desc")
    enriched = []
    for report in reports:
        if not report.get("name") or not report.get("description"):
            continue

        # Get entities linked to this report
        report_id = report["id"]
        entities = {"malware": [], "intrusion_set": [], "attack_pattern": [], "vulnerability": []}

        try:
            rels = api.stix_core_relationship.list(
                fromId=report_id,
                first=50,
                relationship_type=["related-to", "uses", "targets", "indicates"],
            )
            for rel in rels:
                to_entity = rel.get("to", {})
                entity_type = to_entity.get("entity_type", "")
                entity_name = to_entity.get("name", "")
                if entity_type in entities and entity_name:
                    entities[entity_type].append(entity_name)
        except Exception:
            pass

        enriched.append(
            {
                "id": report_id,
                "name": report["name"],
                "description": report.get("description", "")[:3000],
                "created": report.get("created", ""),
                "entities": entities,
            }
        )
    return enriched


def pull_intrusion_sets_with_malware(api, limit: int = 20) -> List[Dict]:
    """Pull intrusion sets (threat actors) with their associated malware/tools."""
    intrusion_sets = api.intrusion_set.list(first=limit)
    results = []
    for iset in intrusion_sets:
        name = iset.get("name", "")
        if not name:
            continue

        # Get malware used by this intrusion set
        malware_used = []
        tools_used = []
        try:
            rels = api.stix_core_relationship.list(
                fromId=iset["id"], first=30, relationship_type=["uses"]
            )
            for rel in rels:
                to_entity = rel.get("to", {})
                if to_entity.get("entity_type") == "Malware":
                    malware_used.append(to_entity.get("name", ""))
                elif to_entity.get("entity_type") == "Tool":
                    tools_used.append(to_entity.get("name", ""))
        except Exception:
            pass

        results.append(
            {
                "id": iset["id"],
                "name": name,
                "description": iset.get("description", ""),
                "aliases": iset.get("aliases", []) or [],
                "malware": malware_used,
                "tools": tools_used,
            }
        )
    return results


def pull_attack_patterns(api, limit: int = 50) -> List[Dict]:
    """Pull ATT&CK techniques with their MITRE IDs."""
    patterns = api.attack_pattern.list(first=limit)
    results = []
    for p in patterns:
        ext_refs = p.get("externalReferences", []) or []
        mitre_id = ""
        for ref in ext_refs:
            if ref.get("source_name") in (
                "mitre-attack",
                "mitre-mobile-attack",
                "mitre-ics-attack",
            ):
                mitre_id = ref.get("external_id", "")
                break
        results.append(
            {
                "id": p["id"],
                "name": p.get("name", ""),
                "description": p.get("description", "")[:500],
                "mitre_id": mitre_id,
            }
        )
    return results


# ── QA Generation ───────────────────────────────────────────────────────────


def generate_qa_from_opencti(
    reports: List[Dict],
    intrusion_sets: List[Dict],
    attack_patterns: List[Dict],
    max_queries: int = 30,
) -> List[Dict]:
    """Generate QA pairs from OpenCTI structured data as ground truth."""
    qa_pairs = []

    # Category 1: Report retrieval — "What does report X say about Y?"
    for report in reports[: max_queries // 4]:
        if report["entities"]["malware"]:
            malware = report["entities"]["malware"][0]
            qa_pairs.append(
                {
                    "category": "report_retrieval",
                    "question": f"What reports discuss {malware}?",
                    "expected_entity": malware,
                    "expected_report": report["name"],
                    "ground_truth_source": "opencti_relationship",
                }
            )

    # Category 2: Attribution — "What malware does [actor] use?"
    for iset in intrusion_sets:
        if iset["malware"]:
            qa_pairs.append(
                {
                    "category": "attribution",
                    "question": f"What malware does {iset['name']} use?",
                    "expected_values": iset["malware"],
                    "actor_name": iset["name"],
                    "actor_aliases": iset["aliases"],
                    "ground_truth_source": "opencti_uses_relationship",
                }
            )

    # Category 3: Technique lookup — "What is T1071?"
    for pattern in attack_patterns[: max_queries // 4]:
        if pattern["mitre_id"]:
            qa_pairs.append(
                {
                    "category": "technique_lookup",
                    "question": f"What is {pattern['mitre_id']}?",
                    "expected_name": pattern["name"],
                    "mitre_id": pattern["mitre_id"],
                    "ground_truth_source": "opencti_attack_pattern",
                }
            )

    # Category 4: Negative knowledge — actors NOT in OpenCTI
    fake_actors = ["APT99", "DarkPhoenix Group", "Operation Midnight Star"]
    for fake in fake_actors:
        qa_pairs.append(
            {
                "category": "negative_knowledge",
                "question": f"What tools does {fake} use?",
                "expected_count": 0,
                "ground_truth_source": "synthetic_negative",
            }
        )

    return qa_pairs[:max_queries]


# ── Scoring ─────────────────────────────────────────────────────────────────


def score_retrieval(retrieved_text: str, expected: str) -> float:
    """Check if expected entity/value appears in retrieved context."""
    return 1.0 if expected.lower() in retrieved_text.lower() else 0.0


def score_set_retrieval(retrieved_text: str, expected_values: List[str]) -> Dict:
    """Set-based scoring for multi-value retrieval (e.g., malware list)."""
    text_lower = retrieved_text.lower()
    found = {v for v in expected_values if v.lower() in text_lower}
    if not expected_values:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
    recall = len(found) / len(expected_values)
    precision = len(found) / max(len(found), 1)
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


# ── Benchmark Runner ────────────────────────────────────────────────────────


def run_benchmark(
    url: str = "http://localhost:8080",
    token: str = "",
    max_reports: int = 20,
    max_queries: int = 30,
    k: int = 10,
) -> Dict:
    """Run the OpenCTI live benchmark."""
    print("=" * 70)
    print("  OpenCTI Live Benchmark — Real CTI Data")
    print(f"  Date: {datetime.now().isoformat()}")
    print(f"  Version: ZettelForge {__version__}")
    print(f"  OpenCTI: {url}")
    print(f"  Reports: {max_reports}, Queries: {max_queries}, k: {k}")
    print("=" * 70)

    # Connect to OpenCTI
    print("\n[1/5] Connecting to OpenCTI...")
    api = get_opencti_client(url, token)
    print("  Connected")

    # Pull data
    print("\n[2/5] Pulling data from OpenCTI...")
    reports = pull_reports_with_entities(api, limit=max_reports)
    intrusion_sets = pull_intrusion_sets_with_malware(api, limit=20)
    attack_patterns = pull_attack_patterns(api, limit=50)
    print(f"  Reports: {len(reports)}")
    print(f"  Intrusion sets: {len(intrusion_sets)}")
    print(f"  Attack patterns: {len(attack_patterns)}")

    # Count entities across reports
    entity_counts = Counter()
    for r in reports:
        for etype, values in r["entities"].items():
            entity_counts[etype] += len(values)
    print(f"  Report-linked entities: {dict(entity_counts)}")

    # Generate QA pairs
    qa_pairs = generate_qa_from_opencti(reports, intrusion_sets, attack_patterns, max_queries)
    cat_counts = Counter(q["category"] for q in qa_pairs)
    print(f"  QA pairs: {len(qa_pairs)}")
    for cat, count in cat_counts.most_common():
        print(f"    {cat}: {count}")

    # Ingest into ZettelForge
    print(f"\n[3/5] Ingesting {len(reports)} reports into ZettelForge...")
    tmpdir = tempfile.mkdtemp(prefix="opencti_bench_")
    mm = MemoryManager(
        jsonl_path=f"{tmpdir}/notes.jsonl",
        lance_path=f"{tmpdir}/vectordb",
    )

    start = time.perf_counter()
    ingested = 0
    for report in reports:
        content = f"# {report['name']}\n\n{report['description']}"
        try:
            mm.remember(
                content=content,
                source_type="opencti_report",
                source_ref=f"opencti:{report['id']}",
                domain="cti",
            )
            ingested += 1
        except Exception:
            if ingested == 0:
                raise
    ingest_time = time.perf_counter() - start
    print(f"  Ingested {ingested} reports in {ingest_time:.1f}s")

    # Also ingest intrusion set descriptions for attribution queries
    for iset in intrusion_sets:
        if iset["description"]:
            content = f"# {iset['name']}\n\nAliases: {', '.join(iset['aliases'])}\n\n{iset['description']}"
            if iset["malware"]:
                content += f"\n\nMalware used: {', '.join(iset['malware'])}"
            if iset["tools"]:
                content += f"\n\nTools used: {', '.join(iset['tools'])}"
            try:
                mm.remember(content=content, source_type="opencti_intrusion_set", domain="cti")
                ingested += 1
            except Exception:
                pass
    print(f"  Total ingested: {ingested} (reports + intrusion sets)")

    # Evaluate
    print(f"\n[4/5] Evaluating {len(qa_pairs)} queries...")
    results_by_cat = defaultdict(list)

    for i, qa in enumerate(qa_pairs):
        cat = qa["category"]
        start_q = time.perf_counter()

        if cat == "report_retrieval":
            results = mm.recall(qa["question"], k=k, domain="cti")
            context = " ".join(n.content.raw for n in results)
            latency = time.perf_counter() - start_q
            score = score_retrieval(context, qa["expected_entity"])
            results_by_cat[cat].append({"score": score, "latency_s": latency})

        elif cat == "attribution":
            results = mm.recall(qa["question"], k=k, domain="cti")
            context = " ".join(n.content.raw for n in results)
            latency = time.perf_counter() - start_q
            scores = score_set_retrieval(context, qa["expected_values"])
            results_by_cat[cat].append(
                {"f1": scores["f1"], "recall": scores["recall"], "latency_s": latency}
            )

        elif cat == "technique_lookup":
            results = mm.recall(qa["question"], k=k, domain="cti")
            context = " ".join(n.content.raw for n in results)
            latency = time.perf_counter() - start_q
            score = score_retrieval(context, qa["expected_name"])
            results_by_cat[cat].append({"score": score, "latency_s": latency})

        elif cat == "negative_knowledge":
            results = mm.recall(qa["question"], k=k, domain="cti")
            latency = time.perf_counter() - start_q
            score = (
                1.0
                if len(results) == 0
                or not any(
                    qa["question"].split("does ")[-1].split(" use")[0].lower()
                    in n.content.raw.lower()
                    for n in results
                )
                else 0.0
            )
            results_by_cat[cat].append({"score": score, "latency_s": latency})

    # Report
    print("\n[5/5] Results")
    print("=" * 70)
    print(f"{'Category':<25} {'Score':>10} {'p50 Lat':>10} {'N':>5}")
    print("-" * 70)

    overall_scores = []
    overall_latencies = []

    for cat in ["report_retrieval", "attribution", "technique_lookup", "negative_knowledge"]:
        items = results_by_cat.get(cat, [])
        if not items:
            print(f"{cat:<25} {'--':>10} {'--':>10} {'0':>5}")
            continue

        avg_score = statistics.mean(r.get("f1", r.get("score", 0)) for r in items)
        p50 = statistics.median(r["latency_s"] for r in items)

        print(f"{cat:<25} {avg_score:>9.1%} {p50 * 1000:>8.0f}ms {len(items):>5}")
        overall_scores.extend([avg_score] * len(items))
        overall_latencies.extend(r["latency_s"] for r in items)

    print("-" * 70)
    if overall_scores:
        oa = statistics.mean(overall_scores)
        ol = statistics.median(overall_latencies)
        print(f"{'OVERALL':<25} {oa:>9.1%} {ol * 1000:>8.0f}ms {len(overall_scores):>5}")
    print("=" * 70)

    # Save results
    output = {
        "meta": {
            "date": datetime.now().isoformat(),
            "version": f"zettelforge-{__version__}",
            "opencti_url": url,
            "reports_ingested": ingested,
            "queries": len(qa_pairs),
            "k": k,
            "data_source": "live_opencti",
        },
        "opencti_stats": {
            "reports": len(reports),
            "intrusion_sets": len(intrusion_sets),
            "attack_patterns": len(attack_patterns),
        },
        "by_category": {
            cat: {
                "avg_score": statistics.mean(r.get("f1", r.get("score", 0)) for r in items),
                "p50_latency_ms": round(statistics.median(r["latency_s"] for r in items) * 1000, 1),
                "n": len(items),
            }
            for cat, items in results_by_cat.items()
        },
        "overall": {
            "avg_score": round(statistics.mean(overall_scores), 4) if overall_scores else 0,
            "p50_latency_ms": round(statistics.median(overall_latencies) * 1000, 1)
            if overall_latencies
            else 0,
        },
    }

    results_path = Path(__file__).parent / "opencti_results.json"
    with open(results_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {results_path}")

    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OpenCTI Live Benchmark")
    parser.add_argument("--url", default=os.environ.get("OPENCTI_URL", "http://localhost:8080"))
    parser.add_argument("--token", default=os.environ.get("OPENCTI_TOKEN", ""))
    parser.add_argument("--reports", type=int, default=20, help="Reports to pull (default: 20)")
    parser.add_argument("--queries", type=int, default=30, help="QA pairs (default: 30)")
    parser.add_argument("--k", type=int, default=10, help="Top-k retrieval (default: 10)")
    args = parser.parse_args()

    if not args.token:
        print("ERROR: Set OPENCTI_TOKEN env var or pass --token")
        exit(1)

    run_benchmark(
        url=args.url,
        token=args.token,
        max_reports=args.reports,
        max_queries=args.queries,
        k=args.k,
    )
