#!/usr/bin/env python3
"""
RAGAS Retrieval Quality Benchmark for ZettelForge
===================================================
Evaluates retrieval quality using RAGAS metrics (NonLLMStringSimilarity,
RougeScore) on the LOCOMO dataset or CTI corpus. No LLM judge needed --
all metrics are computed locally.

Reuses the same LOCOMO data loader and ingestion logic from locomo_benchmark.py.
CTI data is imported from cti_retrieval_benchmark.py.

Usage:
  python benchmarks/ragas_benchmark.py                       # Quick (20 samples, locomo)
  python benchmarks/ragas_benchmark.py --samples 50          # Custom sample size
  python benchmarks/ragas_benchmark.py --k 15                # Custom top-k
  python benchmarks/ragas_benchmark.py --domain cti          # CTI corpus
  python benchmarks/ragas_benchmark.py --domain cti --k 5    # CTI with custom top-k
"""
import argparse
import json
import statistics
import sys
import tempfile
import time
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Tuple

from zettelforge import MemoryManager, __version__

# Skip slow causal extraction during benchmarks -- it calls Ollama per-note
# and adds 5-10s per session.  The RAGAS benchmark measures *retrieval* quality,
# not causal-graph quality, so this is safe to skip.
from zettelforge.note_constructor import NoteConstructor as _NC  # noqa: N814

_NC.extract_causal_triples = lambda self, text, note_id="": []   # no-op

# Reuse LOCOMO data utilities
sys.path.insert(0, str(Path(__file__).parent))
# CTI corpus data
from cti_retrieval_benchmark import CTI_QUERIES, CTI_REPORTS
from locomo_benchmark import (
    CATEGORY_NAMES,
    DATA_FILE,
    flatten_conversations,
    ingest_conversations,
    load_locomo,
    sample_qa_pairs,
)

# -- RAGAS evaluate wrapper ----------------------------------------------------

def _ragas_evaluate(samples: list) -> Tuple[Dict, str]:
    """
    Try RAGAS evaluate(). Returns (scores_dict, method_used).
    Falls back to manual scoring on any failure.
    """
    try:
        from ragas import EvaluationDataset, SingleTurnSample, evaluate
        from ragas.metrics import NonLLMStringSimilarity, RougeScore

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


# -- CTI domain helpers --------------------------------------------------------

def _context_precision(retrieved_contexts: List[str], gold: str) -> float:
    """
    Context precision: fraction of retrieved notes that contain at least one
    gold keyword.  A note is considered relevant if any gold token appears in
    its lowercased text.
    """
    if not retrieved_contexts:
        return 0.0
    gold_tokens = set(gold.lower().split())
    if not gold_tokens:
        return 0.0
    relevant = sum(
        1
        for ctx in retrieved_contexts
        if any(tok in ctx.lower() for tok in gold_tokens)
    )
    return relevant / len(retrieved_contexts)


def run_ragas_benchmark_cti(k: int = 10) -> Dict:
    """Run RAGAS-style retrieval quality benchmark on the CTI corpus."""

    print("=" * 70)
    print("  RAGAS Retrieval Quality Benchmark for ZettelForge  [domain: cti]")
    print(f"  Date: {datetime.now().isoformat()}")
    print(f"  Version: ZettelForge {__version__}")
    print(f"  Reports: {len(CTI_REPORTS)}  |  Queries: {len(CTI_QUERIES)}")
    print(f"  Top-k: {k}")
    print("=" * 70)

    # Ingest CTI reports into a fresh temp instance
    tmpdir = tempfile.mkdtemp(prefix="ragas_cti_bench_")
    mm = MemoryManager(
        jsonl_path=f"{tmpdir}/notes.jsonl",
        lance_path=f"{tmpdir}/vectordb",
    )

    print(f"\n[1/3] Ingesting {len(CTI_REPORTS)} CTI reports...")
    ingest_start = time.perf_counter()
    for report in CTI_REPORTS:
        mm.remember(
            report["content"],
            source_type="threat_report",
            source_ref=report["id"],
            domain="cti",
        )
    ingest_duration = round(time.perf_counter() - ingest_start, 2)
    print(f"  Ingested: {len(CTI_REPORTS)} reports in {ingest_duration}s")

    # Retrieve contexts for each CTI query
    print(f"\n[2/3] Retrieving contexts for {len(CTI_QUERIES)} CTI queries...")
    eval_samples = []
    latencies = []

    for qa in CTI_QUERIES:
        start = time.perf_counter()
        results = mm.recall(qa["question"], k=k, exclude_superseded=False)
        latency = time.perf_counter() - start
        latencies.append(latency)

        retrieved_contexts = [note.content.raw for note in results]
        predicted = " ".join(retrieved_contexts[:3])[:2000]

        eval_samples.append({
            "question": qa["question"],
            "gold_answer": qa["gold"],
            "predicted": predicted,
            "retrieved_contexts": retrieved_contexts,
            "category": qa["category"],
            "retrieved_count": len(results),
        })

    # Score: keyword_presence + context_precision
    print("\n[3/3] Computing RAGAS metrics...")
    manual_scores = _manual_score(eval_samples)

    # context_precision is a CTI-domain addition on top of manual scoring
    cp_scores = [
        _context_precision(s["retrieved_contexts"], s["gold_answer"])
        for s in eval_samples
    ]
    scores = {
        "context_precision": round(statistics.mean(cp_scores), 4),
        **manual_scores,
    }
    method = "manual_fallback+context_precision"

    # Per-category breakdown
    by_cat: Dict[str, Dict] = {}
    for s, cp in zip(eval_samples, cp_scores):
        cat = s["category"]
        if cat not in by_cat:
            by_cat[cat] = {"count": 0, "retrieved_counts": [], "cp": []}
        by_cat[cat]["count"] += 1
        by_cat[cat]["retrieved_counts"].append(s["retrieved_count"])
        by_cat[cat]["cp"].append(cp)

    # Latency stats
    p50_lat = statistics.median(latencies) * 1000
    p95_lat = (
        sorted(latencies)[int(len(latencies) * 0.95)] * 1000
        if len(latencies) >= 2
        else latencies[0] * 1000
    )

    # Report
    print("\n" + "=" * 70)
    print("  RAGAS Results  [domain: cti]")
    print("=" * 70)
    print(f"  Scoring method: {method}")
    for metric, value in scores.items():
        print(f"  {metric}: {value:.4f}")
    print(f"  p50 retrieval latency: {p50_lat:.0f}ms")
    print(f"  p95 retrieval latency: {p95_lat:.0f}ms")
    print(f"  Total QA pairs evaluated: {len(eval_samples)}")

    print("\n  Per-category breakdown:")
    for cat in ["tool-attribution", "cve-linkage", "attribution", "temporal", "multi-hop"]:
        info = by_cat.get(cat)
        if info:
            avg_cp = round(statistics.mean(info["cp"]), 3)
            print(f"    {cat}: n={info['count']}, context_precision={avg_cp:.3f}")

    # Build output
    output = {
        "meta": {
            "date": datetime.now().isoformat(),
            "version": f"zettelforge-{__version__}",
            "dataset": "cti_corpus",
            "reports": len(CTI_REPORTS),
            "queries": len(CTI_QUERIES),
            "k": k,
            "scoring_method": method,
        },
        "ingest": {
            "ingested": len(CTI_REPORTS),
            "duration_s": ingest_duration,
        },
        "scores": scores,
        "latency": {
            "p50_ms": round(p50_lat, 1),
            "p95_ms": round(p95_lat, 1),
        },
        "by_category": {
            cat: {
                "n": info["count"],
                "context_precision": round(statistics.mean(info["cp"]), 4),
                "avg_retrieved": round(statistics.mean(info["retrieved_counts"]), 1),
            }
            for cat, info in by_cat.items()
        },
        "total_samples": len(eval_samples),
    }

    results_path = Path(__file__).parent / "ragas_cti_results.json"
    with open(results_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved: {results_path}")

    return output


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
    print("\n[4/4] Computing RAGAS metrics...")
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

    print("\n  Per-category sample counts:")
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
    parser.add_argument(
        "--domain",
        type=str,
        default="locomo",
        choices=["locomo", "cti"],
        help="Evaluation domain: 'locomo' (default) or 'cti'",
    )
    args = parser.parse_args()

    if args.domain == "cti":
        run_ragas_benchmark_cti(k=args.k)
    else:
        data_path = Path(args.data) if args.data else DATA_FILE
        run_ragas_benchmark(
            data_path=data_path,
            per_category=args.samples,
            k=args.k,
        )
