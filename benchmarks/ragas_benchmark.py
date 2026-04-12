#!/usr/bin/env python3
"""
RAGAS Retrieval Quality Benchmark for ZettelForge
===================================================
Evaluates retrieval quality using RAGAS metrics (NonLLMStringSimilarity,
RougeScore) on the LOCOMO dataset. No LLM judge needed -- all metrics
are computed locally.

Reuses the same LOCOMO data loader and ingestion logic from locomo_benchmark.py.

Usage:
  python benchmarks/ragas_benchmark.py                    # Quick (20 samples)
  python benchmarks/ragas_benchmark.py --samples 50       # Custom sample size
  python benchmarks/ragas_benchmark.py --k 15             # Custom top-k
"""
import json
import sys
import time
import tempfile
import argparse
import statistics
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from difflib import SequenceMatcher

from zettelforge import MemoryManager, __version__

# Skip slow causal extraction during benchmarks -- it calls Ollama per-note
# and adds 5-10s per session.  The RAGAS benchmark measures *retrieval* quality,
# not causal-graph quality, so this is safe to skip.
from zettelforge.note_constructor import NoteConstructor as _NC
_NC.extract_causal_triples = lambda self, text, note_id="": []   # no-op

# Reuse LOCOMO data utilities
sys.path.insert(0, str(Path(__file__).parent))
from locomo_benchmark import (
    load_locomo,
    flatten_conversations,
    sample_qa_pairs,
    ingest_conversations,
    DATA_FILE,
    CATEGORY_NAMES,
)


# -- RAGAS evaluate wrapper ----------------------------------------------------

def _ragas_evaluate(samples: list) -> Tuple[Dict, str]:
    """
    Try RAGAS evaluate(). Returns (scores_dict, method_used).
    Falls back to manual scoring on any failure.
    """
    try:
        from ragas.metrics import NonLLMStringSimilarity, RougeScore
        from ragas import evaluate, EvaluationDataset, SingleTurnSample

        ragas_samples = []
        for s in samples:
            ragas_samples.append(SingleTurnSample(
                user_input=s["question"],
                retrieved_contexts=s["retrieved_contexts"],
                reference=s["gold_answer"],
                response=s["predicted"],
            ))

        dataset = EvaluationDataset(samples=ragas_samples)
        metrics = [NonLLMStringSimilarity(), RougeScore()]
        result = evaluate(dataset=dataset, metrics=metrics)

        # Extract scores from result
        scores = result.to_pandas()
        score_dict = {}
        for col in scores.columns:
            if col not in ("user_input", "retrieved_contexts", "reference", "response"):
                vals = scores[col].dropna().tolist()
                if vals:
                    score_dict[col] = round(statistics.mean(vals), 4)

        return score_dict, "ragas_evaluate"

    except Exception as e:
        print(f"  RAGAS evaluate() failed: {e}")
        print("  Falling back to manual scoring...")
        return _manual_score(samples), "manual_fallback"


def _manual_score(samples: list) -> Dict:
    """
    Manual fallback: compute string similarity and keyword presence
    without depending on RAGAS evaluate().
    """
    string_sims = []
    presence_scores = []

    for s in samples:
        gold = s["gold_answer"].lower()
        context_joined = " ".join(s["retrieved_contexts"]).lower()

        # String similarity (SequenceMatcher ratio)
        sim = SequenceMatcher(None, gold, context_joined[:len(gold) * 3]).ratio()
        string_sims.append(sim)

        # Keyword presence: what fraction of gold tokens appear in context?
        gold_tokens = set(gold.split())
        if gold_tokens:
            found = sum(1 for t in gold_tokens if t in context_joined)
            presence_scores.append(found / len(gold_tokens))
        else:
            presence_scores.append(0.0)

    return {
        "string_similarity": round(statistics.mean(string_sims), 4),
        "keyword_presence": round(statistics.mean(presence_scores), 4),
    }


# -- Main benchmark ------------------------------------------------------------

def run_ragas_benchmark(
    data_path: Path = DATA_FILE,
    per_category: int = 20,
    k: int = 10,
) -> Dict:
    """Run RAGAS retrieval quality benchmark on LOCOMO data."""

    print("=" * 70)
    print("  RAGAS Retrieval Quality Benchmark for ZettelForge")
    print(f"  Date: {datetime.now().isoformat()}")
    print(f"  Version: ZettelForge {__version__}")
    print(f"  Dataset: {data_path.name}")
    print(f"  Samples per category: {per_category}")
    print(f"  Top-k: {k}")
    print("=" * 70)

    # Load data
    print("\n[1/4] Loading LoCoMo dataset...")
    data = load_locomo(data_path)
    all_turns = flatten_conversations(data)
    qa_pairs = sample_qa_pairs(data, per_category)
    print(f"  Conversations: {len(data)}")
    print(f"  Dialogue turns: {len(all_turns)}")
    print(f"  QA pairs: {len(qa_pairs)}")

    # Ingest into temp ZettelForge
    tmpdir = tempfile.mkdtemp(prefix="ragas_bench_")
    mm = MemoryManager(
        jsonl_path=f"{tmpdir}/notes.jsonl",
        lance_path=f"{tmpdir}/vectordb",
    )

    print(f"\n[2/4] Ingesting {len(all_turns)} dialogue turns...")
    ingest_metrics = ingest_conversations(mm, all_turns)
    print(f"  Ingested: {ingest_metrics['ingested']} sessions")
    print(f"  Duration: {ingest_metrics['duration_s']}s")

    # Retrieve contexts for each QA pair
    print(f"\n[3/4] Retrieving contexts for {len(qa_pairs)} QA pairs...")
    eval_samples = []
    latencies = []

    for i, qa in enumerate(qa_pairs):
        start = time.perf_counter()
        results = mm.recall(qa["question"], k=k, exclude_superseded=False)
        latency = time.perf_counter() - start
        latencies.append(latency)

        retrieved_contexts = [note.content.raw for note in results]
        predicted = " ".join(retrieved_contexts[:3])[:2000]
        gold_answer = str(qa.get("answer", qa.get("adversarial_answer", "")))

        eval_samples.append({
            "question": qa["question"],
            "gold_answer": gold_answer,
            "predicted": predicted,
            "retrieved_contexts": retrieved_contexts,
            "category": CATEGORY_NAMES.get(qa.get("category", 0), "unknown"),
            "retrieved_count": len(results),
        })

        if (i + 1) % 25 == 0:
            print(f"  Retrieved {i + 1}/{len(qa_pairs)}...")

    # Score with RAGAS
    print(f"\n[4/4] Computing RAGAS metrics...")
    scores, method = _ragas_evaluate(eval_samples)

    # Per-category breakdown
    by_cat = {}
    for s in eval_samples:
        cat = s["category"]
        if cat not in by_cat:
            by_cat[cat] = {"count": 0, "retrieved_counts": []}
        by_cat[cat]["count"] += 1
        by_cat[cat]["retrieved_counts"].append(s["retrieved_count"])

    # Latency stats
    p50_lat = statistics.median(latencies) * 1000
    p95_lat = sorted(latencies)[int(len(latencies) * 0.95)] * 1000 if len(latencies) >= 2 else latencies[0] * 1000

    # Report
    print("\n" + "=" * 70)
    print("  RAGAS Results")
    print("=" * 70)
    print(f"  Scoring method: {method}")
    for metric, value in scores.items():
        print(f"  {metric}: {value:.4f}")
    print(f"  p50 retrieval latency: {p50_lat:.0f}ms")
    print(f"  p95 retrieval latency: {p95_lat:.0f}ms")
    print(f"  Total QA pairs evaluated: {len(eval_samples)}")

    print(f"\n  Per-category sample counts:")
    for cat in ["single-hop", "multi-hop", "temporal", "open-domain", "adversarial"]:
        info = by_cat.get(cat, {"count": 0})
        print(f"    {cat}: {info['count']}")

    # Build output
    output = {
        "meta": {
            "date": datetime.now().isoformat(),
            "version": f"zettelforge-{__version__}",
            "dataset": str(data_path),
            "per_category": per_category,
            "k": k,
            "scoring_method": method,
        },
        "ingest": ingest_metrics,
        "scores": scores,
        "latency": {
            "p50_ms": round(p50_lat, 1),
            "p95_ms": round(p95_lat, 1),
        },
        "by_category": {
            cat: {"n": info["count"], "avg_retrieved": round(statistics.mean(info["retrieved_counts"]), 1)}
            for cat, info in by_cat.items()
        },
        "total_samples": len(eval_samples),
    }

    results_path = Path(__file__).parent / "ragas_results.json"
    with open(results_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved: {results_path}")

    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RAGAS Benchmark for ZettelForge")
    parser.add_argument("--samples", type=int, default=20, help="Samples per category (default: 20)")
    parser.add_argument("--k", type=int, default=10, help="Top-k retrieval (default: 10)")
    parser.add_argument("--data", type=str, default=None, help="Path to locomo10.json")
    args = parser.parse_args()

    data_path = Path(args.data) if args.data else DATA_FILE

    run_ragas_benchmark(
        data_path=data_path,
        per_category=args.samples,
        k=args.k,
    )
