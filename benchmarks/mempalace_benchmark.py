#!/usr/bin/env python3
"""
MemPalace Benchmark — Run LOCOMO against MemPalace for comparison.

Uses the same LOCOMO dataset, scoring, and methodology as locomo_benchmark.py
but with MemPalace's ChromaDB-backed memory system instead of ZettelForge.

Usage:
  python benchmarks/mempalace_benchmark.py --samples 20
"""
import json
import sys
import time
import tempfile
import shutil
import argparse
import statistics
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple

sys.path.insert(0, str(Path(__file__).parent))
from locomo_benchmark import (
    load_locomo, flatten_conversations, sample_qa_pairs,
    keyword_judge, CATEGORY_NAMES, DATA_FILE,
)

# MemPalace imports
MEMPALACE_PATH = Path("/home/rolandpg/.openclaw/workspace-nexus/mempalace-test")
sys.path.insert(0, str(MEMPALACE_PATH))


def ingest_to_mempalace(palace_path: str, turns: List[Dict]) -> Dict:
    """Ingest LOCOMO sessions into MemPalace."""
    from mempalace.searcher import search_memories
    import chromadb

    client = chromadb.PersistentClient(path=palace_path)
    collection = client.get_or_create_collection("mempalace_drawers")

    start = time.perf_counter()
    ingested = 0

    # Group turns into sessions (same as ZettelForge benchmark)
    sessions = {}
    for turn in turns:
        key = f"{turn['sample_id']}:{turn['session']}"
        if key not in sessions:
            sessions[key] = {"date": turn["date"], "lines": [], "sample_id": turn["sample_id"], "session": turn["session"]}
        sessions[key]["lines"].append(f"{turn['speaker']}: {turn['text']}")

    for key, session in sessions.items():
        content = f"[{session['date']}] Conversation session {session['session']}:\n" + "\n".join(session["lines"])
        if len(content) > 4000:
            content = content[:4000]

        # Chunk to 800 chars (MemPalace default)
        chunks = []
        if len(content) > 800:
            for i in range(0, len(content), 700):
                chunk = content[i:i+800]
                if len(chunk) > 50:
                    chunks.append(chunk)
        else:
            chunks = [content]

        for i, chunk in enumerate(chunks):
            drawer_id = f"locomo_{session['sample_id']}_s{session['session']}_{i}"
            collection.add(
                ids=[drawer_id],
                documents=[chunk],
                metadatas=[{
                    "wing": "locomo",
                    "room": "session",
                    "source_file": f"locomo_{session['sample_id']}",
                    "chunk_index": i,
                    "added_by": "benchmark",
                    "filed_at": datetime.now().isoformat(),
                }],
            )
            ingested += 1

        if ingested % 100 == 0 and ingested > 0:
            elapsed = time.perf_counter() - start
            print(f"  Ingested {ingested} chunks ({elapsed:.0f}s)...")

    duration = time.perf_counter() - start
    return {
        "ingested": ingested,
        "sessions": len(sessions),
        "duration_s": round(duration, 2),
    }


def recall_mempalace(palace_path: str, question: str, k: int = 10) -> Tuple[str, List[str], float]:
    """Query MemPalace and return context."""
    import chromadb

    start = time.perf_counter()

    client = chromadb.PersistentClient(path=palace_path)
    collection = client.get_or_create_collection("mempalace_drawers")

    results = collection.query(
        query_texts=[question],
        n_results=k,
        where={"wing": "locomo"},
    )

    documents = results.get("documents", [[]])[0]
    ids = results.get("ids", [[]])[0]

    context = "\n".join(documents[:k])
    answer = context[:2000]
    latency = time.perf_counter() - start

    return answer, ids, latency


def run_benchmark(per_category: int = 20, k: int = 10) -> Dict:
    """Run LOCOMO benchmark against MemPalace."""
    print("=" * 70)
    print("  LOCOMO Benchmark for MemPalace")
    print(f"  Date: {datetime.now().isoformat()}")
    print(f"  Samples per category: {per_category}")
    print(f"  Judge: keyword-overlap")
    print("=" * 70)

    # Load data
    print("\n[1/4] Loading LoCoMo dataset...")
    data = load_locomo(DATA_FILE)
    all_turns = flatten_conversations(data)
    qa_pairs = sample_qa_pairs(data, per_category)
    print(f"  Conversations: {len(data)}, Turns: {len(all_turns)}, QA: {len(qa_pairs)}")

    # Create temp palace
    palace_dir = tempfile.mkdtemp(prefix="mempalace_bench_")
    palace_path = f"{palace_dir}/palace"

    # Ingest
    print(f"\n[2/4] Ingesting into MemPalace...")
    ingest_metrics = ingest_to_mempalace(palace_path, all_turns)
    print(f"  Ingested: {ingest_metrics['ingested']} chunks from {ingest_metrics['sessions']} sessions")
    print(f"  Duration: {ingest_metrics['duration_s']}s")

    # Evaluate
    print(f"\n[3/4] Evaluating {len(qa_pairs)} QA pairs...")
    results_by_cat = {}
    all_results = []

    for i, qa in enumerate(qa_pairs):
        cat = qa.get("category", 0)
        cat_name = CATEGORY_NAMES.get(cat, f"cat-{cat}")

        if cat_name not in results_by_cat:
            results_by_cat[cat_name] = {"scores": [], "latencies": [], "retrieved_counts": []}

        answer, evidence_ids, latency = recall_mempalace(palace_path, qa["question"], k=k)
        gold = str(qa.get("answer", qa.get("adversarial_answer", "")))
        score = keyword_judge(answer, gold)

        results_by_cat[cat_name]["scores"].append(score)
        results_by_cat[cat_name]["latencies"].append(latency)
        results_by_cat[cat_name]["retrieved_counts"].append(len(evidence_ids))

        all_results.append({
            "category": cat_name,
            "question": qa["question"],
            "gold_answer": gold,
            "predicted": answer[:500],
            "score": score,
            "latency_s": round(latency, 3),
            "retrieved": len(evidence_ids),
        })

        if (i + 1) % 25 == 0:
            print(f"  Evaluated {i + 1}/{len(qa_pairs)}...")

    # Report
    print(f"\n[4/4] Results")
    print("=" * 70)
    print(f"{'Category':<15} {'Accuracy':>10} {'Avg Score':>10} {'p50 Lat':>10} {'p95 Lat':>10} {'N':>5}")
    print("-" * 70)

    overall_scores = []
    overall_latencies = []

    for cat_name in ["single-hop", "multi-hop", "temporal", "open-domain", "adversarial"]:
        stats = results_by_cat.get(cat_name)
        if not stats or not stats["scores"]:
            continue
        scores = stats["scores"]
        lats = stats["latencies"]
        accuracy = sum(1 for s in scores if s == 1.0) / len(scores) * 100
        avg_score = statistics.mean(scores)
        p50_lat = statistics.median(lats)
        p95_lat = sorted(lats)[int(len(lats) * 0.95)] if len(lats) >= 2 else lats[0]
        print(f"{cat_name:<15} {accuracy:>9.1f}% {avg_score:>9.2f} {p50_lat*1000:>8.0f}ms {p95_lat*1000:>8.0f}ms {len(scores):>5}")
        overall_scores.extend(scores)
        overall_latencies.extend(lats)

    print("-" * 70)
    if overall_scores:
        oa = sum(1 for s in overall_scores if s == 1.0) / len(overall_scores) * 100
        os_avg = statistics.mean(overall_scores)
        ol_p50 = statistics.median(overall_latencies)
        ol_p95 = sorted(overall_latencies)[int(len(overall_latencies) * 0.95)]
        print(f"{'OVERALL':<15} {oa:>9.1f}% {os_avg:>9.2f} {ol_p50*1000:>8.0f}ms {ol_p95*1000:>8.0f}ms {len(overall_scores):>5}")

    print("=" * 70)
    print(f"\n  Comparison:")
    print(f"  {'System':<25} {'Accuracy':>10}")
    print(f"  {'-'*35}")
    print(f"  {'ZettelForge 2.0.0':.<25} {'15.0%':>10}")
    if overall_scores:
        print(f"  {'MemPalace':.<25} {oa:>9.1f}%")

    # Save results
    output = {
        "meta": {
            "date": datetime.now().isoformat(),
            "system": "mempalace",
            "dataset": str(DATA_FILE),
            "per_category": per_category,
            "judge": "keyword",
            "k": k,
        },
        "ingest": ingest_metrics,
        "by_category": {
            cat: {
                "accuracy": sum(1 for s in stats["scores"] if s == 1.0) / len(stats["scores"]) * 100,
                "avg_score": statistics.mean(stats["scores"]),
                "p50_latency_ms": statistics.median(stats["latencies"]) * 1000,
                "n": len(stats["scores"]),
            }
            for cat, stats in results_by_cat.items() if stats["scores"]
        },
        "overall": {
            "accuracy": oa if overall_scores else 0,
            "avg_score": os_avg if overall_scores else 0,
            "p50_latency_ms": ol_p50 * 1000 if overall_scores else 0,
            "total_samples": len(overall_scores),
        },
        "details": all_results,
    }

    results_path = Path(__file__).parent / "mempalace_results.json"
    with open(results_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved: {results_path}")

    # Cleanup
    shutil.rmtree(palace_dir, ignore_errors=True)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LOCOMO Benchmark for MemPalace")
    parser.add_argument("--samples", type=int, default=20)
    parser.add_argument("--k", type=int, default=10)
    args = parser.parse_args()
    run_benchmark(per_category=args.samples, k=args.k)
