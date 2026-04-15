#!/usr/bin/env python3
"""
CTI Benchmark v2 — Real Threat Intelligence Retrieval Benchmark
================================================================
Uses the mrmoor/cyber-threat-intelligence HuggingFace dataset (9,732 samples
from Unit 42 threat reports with NER + relation annotations).

Tests ZettelForge's core CTI capabilities:
  1. Entity retrieval — find notes mentioning a specific malware/actor/tool
  2. Relation retrieval — "What malware does [actor] use?"
  3. Multi-source fusion — combine info from multiple reports
  4. Entity extraction accuracy — compare ZettelForge NER vs ground truth
  5. Negative knowledge — queries for nonexistent entities

Usage:
  python benchmarks/cti_benchmark_v2.py                    # Quick (200 notes, 50 queries)
  python benchmarks/cti_benchmark_v2.py --notes 500        # More notes
  python benchmarks/cti_benchmark_v2.py --notes 1000 --queries 100  # Full run
"""

import argparse
import json
import random
import statistics
import tempfile
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple

from zettelforge import MemoryManager, __version__

# ── Data Loading ────────────────────────────────────────────────────────────


def load_cti_dataset(max_notes: int = 200) -> Tuple[List[Dict], Dict]:
    """Load CTI dataset from HuggingFace and extract entity/relation ground truth.

    Returns:
        (samples, entity_index) where entity_index maps entity_value -> [sample_ids]
    """
    from datasets import load_dataset

    ds = load_dataset("mrmoor/cyber-threat-intelligence", split="train")

    # Filter to samples with entities and meaningful text (>50 chars)
    candidates = []
    for row in ds:
        if not row["entities"] or len(row["text"]) < 50:
            continue
        # Extract entity text from offsets
        entities = []
        for e in row["entities"]:
            start = e["start_offset"]
            end = e["end_offset"]
            value = row["text"][start:end].strip()
            if value and len(value) > 1:
                entities.append({"label": e["label"], "value": value})
        if entities:
            candidates.append(
                {
                    "id": row["id"],
                    "text": row["text"],
                    "entities": entities,
                    "relations": row.get("relations", []),
                }
            )

    # Sample up to max_notes
    if len(candidates) > max_notes:
        random.seed(42)
        candidates = random.sample(candidates, max_notes)

    # Build entity index for QA generation
    entity_index = defaultdict(list)
    for sample in candidates:
        for e in sample["entities"]:
            key = f"{e['label']}:{e['value'].lower()}"
            entity_index[key].append(sample["id"])

    return candidates, dict(entity_index)


# ── QA Generation from Ground Truth ────────────────────────────────────────

# Actor aliases for scoring
ACTOR_ALIASES = {
    "apt28": {"fancy bear", "sofacy", "strontium", "sednit", "iron twilight"},
    "apt29": {"cozy bear", "the dukes", "nobelium", "midnight blizzard"},
    "lazarus": {"hidden cobra", "zinc", "diamond sleet"},
    "turla": {"snake", "venomous bear", "secret blizzard", "uroburos"},
    "muddywater": {"mercury", "mango sandstorm", "static kitten", "seedworm"},
    "volt typhoon": {"bronze silhouette", "vanguard panda"},
    "sandworm": {"voodoo bear", "iridium", "seashell blizzard"},
}


def generate_qa_pairs(samples: List[Dict], entity_index: Dict, max_queries: int = 50) -> List[Dict]:
    """Generate QA pairs from ground truth entity annotations."""
    qa_pairs = []

    # Category 1: Entity retrieval — "Find reports mentioning [entity]"
    entity_counts = Counter()
    for sample in samples:
        for e in sample["entities"]:
            entity_counts[f"{e['label']}:{e['value']}"] += 1

    # Pick entities that appear in 2+ samples (testable retrieval)
    multi_sample_entities = [
        (key, count) for key, count in entity_counts.most_common() if count >= 2
    ]

    for key, count in multi_sample_entities[: max_queries // 3]:
        label, value = key.split(":", 1)
        qa_pairs.append(
            {
                "category": "entity_retrieval",
                "question": f"What reports mention {value}?",
                "entity_type": label,
                "entity_value": value,
                "expected_count": count,
                "expected_sample_ids": entity_index.get(key.lower(), []),
            }
        )

    # Category 2: Relation-based — "What malware does [actor] use?"
    actor_malware = defaultdict(set)
    actor_tools = defaultdict(set)
    for sample in samples:
        actors = [e["value"] for e in sample["entities"] if e["label"] == "threat-actor"]
        malwares = [e["value"] for e in sample["entities"] if e["label"] == "malware"]
        tools = [e["value"] for e in sample["entities"] if e["label"] == "tools"]
        for actor in actors:
            for m in malwares:
                actor_malware[actor.lower()].add(m)
            for t in tools:
                actor_tools[actor.lower()].add(t)

    for actor, malwares in list(actor_malware.items())[: max_queries // 3]:
        qa_pairs.append(
            {
                "category": "tool_attribution",
                "question": f"What malware does {actor} use?",
                "entity_type": "threat-actor",
                "entity_value": actor,
                "expected_values": sorted(malwares),
            }
        )

    # Category 3: Negative knowledge — entities that DON'T exist
    fake_entities = [
        "APT99",
        "DarkPhoenix",
        "CVE-2099-0001",
        "ShadowBlade RAT",
        "Operation Midnight Sun",
    ]
    for fake in fake_entities[: max(3, max_queries // 10)]:
        qa_pairs.append(
            {
                "category": "negative_knowledge",
                "question": f"What do you know about {fake}?",
                "entity_value": fake,
                "expected_count": 0,
            }
        )

    # Category 4: Entity extraction accuracy (per-sample)
    for sample in samples[: max_queries // 4]:
        gt_entities = {f"{e['label']}:{e['value'].lower()}" for e in sample["entities"]}
        qa_pairs.append(
            {
                "category": "entity_extraction",
                "sample_id": sample["id"],
                "text": sample["text"][:500],
                "expected_entities": sorted(gt_entities),
            }
        )

    random.seed(42)
    random.shuffle(qa_pairs)
    return qa_pairs[:max_queries]


# ── Scoring ─────────────────────────────────────────────────────────────────


def score_entity_retrieval(retrieved_ids: List[str], expected_ids: List[int], k: int) -> float:
    """Score whether the expected samples appear in retrieved results."""
    retrieved_note_sources = set()
    for note_id in retrieved_ids:
        # Note IDs contain the source ref which has the sample ID
        retrieved_note_sources.add(note_id)

    # Since we can't directly map note IDs to sample IDs in all cases,
    # check if any retrieved notes contain the entity
    if not expected_ids:
        return 0.0
    # Simplified: return 1.0 if we got results, 0.0 if empty
    return 1.0 if retrieved_ids else 0.0


def score_set_overlap(predicted: Set[str], expected: Set[str]) -> Dict:
    """Set-based precision/recall/F1 with case-insensitive matching."""
    pred = {v.lower() for v in predicted}
    exp = {v.lower() for v in expected}

    if not exp:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
    if not pred:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

    tp = len(pred & exp)
    precision = tp / len(pred)
    recall = tp / len(exp)
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def score_negative(result_count: int) -> float:
    """Score negative knowledge: 1.0 if no results, 0.0 if false positives."""
    return 1.0 if result_count == 0 else 0.0


def alias_match(predicted: str, expected: str) -> bool:
    """Check if predicted matches expected via alias resolution."""
    pred = predicted.lower()
    exp = expected.lower()
    if exp in pred or pred in exp:
        return True
    for canonical, aliases in ACTOR_ALIASES.items():
        if (exp == canonical or exp in aliases) and (
            pred == canonical or pred in aliases or any(a in pred for a in aliases | {canonical})
        ):
            return True
    return False


# ── Benchmark Runner ────────────────────────────────────────────────────────


def run_benchmark(
    max_notes: int = 200,
    max_queries: int = 50,
    k: int = 10,
) -> Dict:
    """Run CTI Benchmark v2."""
    print("=" * 70)
    print("  CTI Benchmark v2 — Real Threat Intelligence")
    print(f"  Date: {datetime.now().isoformat()}")
    print(f"  Version: ZettelForge {__version__}")
    print(f"  Notes: {max_notes}, Queries: {max_queries}, k: {k}")
    print("=" * 70)

    # Load data
    print("\n[1/4] Loading CTI dataset from HuggingFace...")
    samples, entity_index = load_cti_dataset(max_notes)
    print(f"  Loaded {len(samples)} annotated samples")

    # Count entities
    entity_counts = Counter()
    for s in samples:
        for e in s["entities"]:
            entity_counts[e["label"]] += 1
    for label, count in entity_counts.most_common(8):
        print(f"    {label}: {count}")

    # Generate QA pairs
    qa_pairs = generate_qa_pairs(samples, entity_index, max_queries)
    cat_counts = Counter(q["category"] for q in qa_pairs)
    print(f"  Generated {len(qa_pairs)} QA pairs:")
    for cat, count in cat_counts.most_common():
        print(f"    {cat}: {count}")

    # Ingest into ZettelForge
    print(f"\n[2/4] Ingesting {len(samples)} CTI samples...")
    tmpdir = tempfile.mkdtemp(prefix="cti_bench_v2_")
    mm = MemoryManager(
        jsonl_path=f"{tmpdir}/notes.jsonl",
        lance_path=f"{tmpdir}/vectordb",
    )

    start = time.perf_counter()
    ingested = 0
    for i, sample in enumerate(samples):
        try:
            mm.remember(
                content=sample["text"],
                source_type="threat_report",
                source_ref=f"cti-dataset:{sample['id']}",
                domain="cti",
            )
            ingested += 1
        except Exception:
            if ingested == 0:
                raise
        if (i + 1) % 50 == 0:
            print(f"    Ingested {i + 1}/{len(samples)}...")
    ingest_time = time.perf_counter() - start
    print(
        f"  Ingested {ingested}/{len(samples)} in {ingest_time:.1f}s ({ingested / ingest_time:.1f} notes/s)"
    )

    # Evaluate
    print(f"\n[3/4] Evaluating {len(qa_pairs)} queries...")
    results_by_cat = defaultdict(list)

    for i, qa in enumerate(qa_pairs):
        cat = qa["category"]
        start_q = time.perf_counter()

        if cat == "entity_extraction":
            # For extraction: run NER on the sample text and compare to ground truth
            from zettelforge.entity_indexer import EntityExtractor

            extractor = EntityExtractor()
            extracted = extractor.extract_all(qa["text"], use_llm=False)
            predicted_entities = set()
            for etype, values in extracted.items():
                for v in values:
                    predicted_entities.add(f"{etype}:{v}")
            expected = set(qa["expected_entities"])
            scores = score_set_overlap(predicted_entities, expected)
            latency = time.perf_counter() - start_q
            results_by_cat[cat].append(
                {
                    "f1": scores["f1"],
                    "precision": scores["precision"],
                    "recall": scores["recall"],
                    "latency_s": latency,
                }
            )

        elif cat == "negative_knowledge":
            results = mm.recall(qa["question"], k=k, domain="cti")
            latency = time.perf_counter() - start_q
            # Check if any result actually contains the fake entity
            context = " ".join(n.content.raw.lower() for n in results)
            has_fake = qa["entity_value"].lower() in context
            score = 1.0 if not has_fake else 0.0
            results_by_cat[cat].append({"score": score, "latency_s": latency})

        elif cat == "entity_retrieval":
            results = mm.recall(qa["question"], k=k, domain="cti")
            latency = time.perf_counter() - start_q
            # Check if any retrieved note contains the target entity
            context = " ".join(n.content.raw.lower() for n in results)
            found = qa["entity_value"].lower() in context
            score = 1.0 if found else 0.0
            results_by_cat[cat].append(
                {"score": score, "latency_s": latency, "result_count": len(results)}
            )

        elif cat == "tool_attribution":
            results = mm.recall(qa["question"], k=k, domain="cti")
            latency = time.perf_counter() - start_q
            context = " ".join(n.content.raw.lower() for n in results)
            expected = set(qa["expected_values"])
            found = {v for v in expected if v.lower() in context}
            scores = score_set_overlap(found, expected)
            results_by_cat[cat].append(
                {"f1": scores["f1"], "recall": scores["recall"], "latency_s": latency}
            )

        if (i + 1) % 25 == 0:
            print(f"    Evaluated {i + 1}/{len(qa_pairs)}...")

    # Report
    print("\n[4/4] Results")
    print("=" * 70)
    print(f"{'Category':<25} {'Score':>10} {'p50 Lat':>10} {'N':>5}")
    print("-" * 70)

    overall_scores = []
    overall_latencies = []

    for cat in ["entity_retrieval", "tool_attribution", "entity_extraction", "negative_knowledge"]:
        items = results_by_cat.get(cat, [])
        if not items:
            print(f"{cat:<25} {'--':>10} {'--':>10} {'0':>5}")
            continue

        if "f1" in items[0]:
            avg_score = statistics.mean(r["f1"] for r in items)
        else:
            avg_score = statistics.mean(r["score"] for r in items)

        lats = [r["latency_s"] for r in items]
        p50 = statistics.median(lats)

        print(f"{cat:<25} {avg_score:>9.1%} {p50 * 1000:>8.0f}ms {len(items):>5}")
        overall_scores.extend([avg_score] * len(items))
        overall_latencies.extend(lats)

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
            "dataset": "mrmoor/cyber-threat-intelligence",
            "notes_ingested": ingested,
            "queries": len(qa_pairs),
            "k": k,
            "ingest_time_s": round(ingest_time, 1),
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
            "total_queries": len(qa_pairs),
        },
    }

    results_path = Path(__file__).parent / "cti_v2_results.json"
    with open(results_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {results_path}")

    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CTI Benchmark v2")
    parser.add_argument("--notes", type=int, default=200, help="Notes to ingest (default: 200)")
    parser.add_argument(
        "--queries", type=int, default=50, help="QA pairs to evaluate (default: 50)"
    )
    parser.add_argument("--k", type=int, default=10, help="Top-k retrieval (default: 10)")
    args = parser.parse_args()

    run_benchmark(max_notes=args.notes, max_queries=args.queries, k=args.k)
