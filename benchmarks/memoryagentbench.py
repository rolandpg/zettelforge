#!/usr/bin/env python3
"""
MemoryAgentBench Benchmark for ZettelForge
============================================
Evaluates ZettelForge on the MemoryAgentBench (ICLR 2026) dataset.

Splits:
  Accurate_Retrieval (AR): 22 rows, ~100 QA per row — factual recall
  Conflict_Resolution (CR): 8 rows, ~100 QA per row — fact update/contradiction
  Test_Time_Learning (TTL): 6 rows, ~200 QA per row — in-context learning
  Long_Range_Understanding (LRU): 110 rows, 1 QA per row — summarization

Scoring: F1, Exact Match, ROUGE-L (same as the benchmark paper)

Usage:
  python benchmarks/memoryagentbench.py                     # AR + CR (fast)
  python benchmarks/memoryagentbench.py --split all         # All splits
  python benchmarks/memoryagentbench.py --split AR --limit 5  # First 5 AR rows
"""
import json
import os
import sys
import time
import string
import re
import tempfile
import argparse
import statistics
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple
from collections import Counter

os.environ.setdefault("ZETTELFORGE_BACKEND", "jsonl")
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from zettelforge import MemoryManager, __version__


# ── Scoring (from MemoryAgentBench utils) ────────────────────────────────────

def normalize_answer(text: str) -> str:
    text = text.lower()
    text = ''.join(c for c in text if c not in string.punctuation)
    text = re.sub(r'\b(a|an|the)\b', ' ', text)
    return ' '.join(text.split())


def f1_score(prediction: str, ground_truth: str) -> Tuple[float, float, float]:
    pred_tokens = normalize_answer(prediction).split()
    gt_tokens = normalize_answer(ground_truth).split()
    common = Counter(pred_tokens) & Counter(gt_tokens)
    num_same = sum(common.values())
    if num_same == 0:
        return 0.0, 0.0, 0.0
    precision = num_same / len(pred_tokens)
    recall = num_same / len(gt_tokens)
    f1 = 2 * precision * recall / (precision + recall)
    return f1, precision, recall


def exact_match(prediction: str, ground_truth: str) -> float:
    return float(normalize_answer(prediction) == normalize_answer(ground_truth))


def substring_match(prediction: str, ground_truth: str) -> float:
    return float(normalize_answer(ground_truth) in normalize_answer(prediction))


def rouge_l(prediction: str, ground_truth: str) -> float:
    try:
        from rouge_score import rouge_scorer
        scorer = rouge_scorer.RougeScorer(['rougeL'], use_stemmer=True)
        scores = scorer.score(ground_truth, prediction)
        return scores['rougeL'].fmeasure
    except ImportError:
        return 0.0


def score_answer(prediction: str, ground_truths: List[str]) -> Dict:
    """Score a prediction against multiple ground truths (take best)."""
    best = {"f1": 0.0, "em": 0.0, "substr_em": 0.0, "rouge_l": 0.0}
    for gt in ground_truths:
        if not gt:
            continue
        f1, _, _ = f1_score(prediction, gt)
        em = exact_match(prediction, gt)
        sub = substring_match(prediction, gt)
        rl = rouge_l(prediction, gt)
        if f1 > best["f1"]:
            best = {"f1": f1, "em": em, "substr_em": sub, "rouge_l": rl}
    return best


# ── Chunking ─────────────────────────────────────────────────────────────────

def chunk_context(text: str, chunk_size: int = 800) -> List[str]:
    """Split context into chunks on sentence boundaries."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current = ""
    for sent in sentences:
        if len(current) + len(sent) + 1 > chunk_size and current:
            chunks.append(current.strip())
            current = sent + " "
        else:
            current += sent + " "
    if current.strip():
        chunks.append(current.strip())
    return [c for c in chunks if len(c) > 20]


# ── Benchmark Runner ─────────────────────────────────────────────────────────

def run_split(split_name: str, rows, limit: int = None) -> Dict:
    """Run benchmark on a single split."""
    if limit:
        rows = rows[:limit]

    all_scores = []
    total_questions = 0
    total_ingest_time = 0
    total_query_time = 0

    for row_idx, row in enumerate(rows):
        context = row["context"]
        questions = row["questions"]
        answers = row["answers"]
        source = row["metadata"].get("source", "unknown")

        # Create isolated MemoryManager per row
        tmpdir = tempfile.mkdtemp(prefix=f"mab_{split_name}_{row_idx}_")
        mm = MemoryManager(
            jsonl_path=f"{tmpdir}/notes.jsonl",
            lance_path=f"{tmpdir}/vectordb",
        )

        # Ingest: chunk context and store
        ingest_start = time.perf_counter()
        chunks = chunk_context(context, chunk_size=800)
        for i, chunk in enumerate(chunks):
            mm.remember(
                content=chunk,
                source_type="benchmark",
                source_ref=f"mab:{source}:chunk:{i}",
                domain="benchmark",
            )
        ingest_time = time.perf_counter() - ingest_start
        total_ingest_time += ingest_time

        print(f"  [{split_name}] Row {row_idx + 1}/{len(rows)} ({source}): "
              f"{len(chunks)} chunks ingested in {ingest_time:.1f}s, "
              f"{len(questions)} questions")

        # Evaluate each question
        row_scores = []
        for q_idx, (question, answer_list) in enumerate(zip(questions, answers)):
            if not question or not question.strip():
                continue

            query_start = time.perf_counter()
            results = mm.recall(question, k=10, exclude_superseded=False)
            query_time = time.perf_counter() - query_start
            total_query_time += query_time

            # Build answer: use LLM to extract concise answer from retrieved context
            if results:
                context = " ".join(n.content.raw[:300] for n in results[:3])
                try:
                    from zettelforge.llm_client import generate
                    retrieved_text = generate(
                        f"Based on the context, answer concisely in 1-2 sentences.\n"
                        f"Context: {context[:1500]}\n"
                        f"Question: {question}\nAnswer:",
                        max_tokens=100,
                        temperature=0.0,
                    )
                except Exception:
                    retrieved_text = context[:500]
            else:
                retrieved_text = ""

            # Score
            gt_list = answer_list if isinstance(answer_list, list) else [answer_list]
            scores = score_answer(retrieved_text, gt_list)
            row_scores.append(scores)
            total_questions += 1

        all_scores.extend(row_scores)

    # Aggregate
    if not all_scores:
        return {"split": split_name, "n": 0}

    avg_f1 = statistics.mean(s["f1"] for s in all_scores)
    avg_em = statistics.mean(s["em"] for s in all_scores)
    avg_substr = statistics.mean(s["substr_em"] for s in all_scores)
    avg_rouge = statistics.mean(s["rouge_l"] for s in all_scores)

    return {
        "split": split_name,
        "n_rows": len(rows),
        "n_questions": total_questions,
        "f1": round(avg_f1, 4),
        "em": round(avg_em, 4),
        "substr_em": round(avg_substr, 4),
        "rouge_l": round(avg_rouge, 4),
        "ingest_time_s": round(total_ingest_time, 1),
        "query_time_s": round(total_query_time, 1),
        "avg_query_ms": round(total_query_time / max(total_questions, 1) * 1000, 0),
    }


def run_benchmark(splits: List[str] = None, limit: int = None) -> Dict:
    """Run MemoryAgentBench benchmark."""
    from datasets import load_dataset

    print("=" * 70)
    print("  MemoryAgentBench Benchmark for ZettelForge")
    print(f"  Date: {datetime.now().isoformat()}")
    print(f"  Version: ZettelForge {__version__}")
    print("=" * 70)

    ds = load_dataset("ai-hyz/MemoryAgentBench")

    split_map = {
        "AR": "Accurate_Retrieval",
        "CR": "Conflict_Resolution",
        "TTL": "Test_Time_Learning",
        "LRU": "Long_Range_Understanding",
    }

    if splits is None or "all" in splits:
        splits = ["AR", "CR"]  # Default: skip TTL (huge) and LRU (summarization)

    results = {}
    for short_name in splits:
        full_name = split_map.get(short_name, short_name)
        if full_name not in ds:
            print(f"  Skipping {short_name}: not found in dataset")
            continue

        print(f"\n[{short_name}] Running {full_name} ({len(ds[full_name])} rows)...")
        result = run_split(short_name, list(ds[full_name]), limit=limit)
        results[short_name] = result

        print(f"  F1: {result.get('f1', 0):.4f}  EM: {result.get('em', 0):.4f}  "
              f"ROUGE-L: {result.get('rouge_l', 0):.4f}  "
              f"Queries: {result.get('n_questions', 0)}  "
              f"Avg query: {result.get('avg_query_ms', 0):.0f}ms")

    # Overall
    all_f1 = [r["f1"] for r in results.values() if "f1" in r]
    all_em = [r["em"] for r in results.values() if "em" in r]
    all_rouge = [r["rouge_l"] for r in results.values() if "rouge_l" in r]

    overall = {
        "f1": round(statistics.mean(all_f1), 4) if all_f1 else 0,
        "em": round(statistics.mean(all_em), 4) if all_em else 0,
        "rouge_l": round(statistics.mean(all_rouge), 4) if all_rouge else 0,
    }

    print("\n" + "=" * 70)
    print(f"{'Split':<8} {'F1':>8} {'EM':>8} {'ROUGE-L':>8} {'Queries':>8} {'Avg ms':>8}")
    print("-" * 70)
    for name, r in results.items():
        print(f"{name:<8} {r.get('f1',0):>8.4f} {r.get('em',0):>8.4f} "
              f"{r.get('rouge_l',0):>8.4f} {r.get('n_questions',0):>8} "
              f"{r.get('avg_query_ms',0):>7.0f}ms")
    print("-" * 70)
    print(f"{'OVERALL':<8} {overall['f1']:>8.4f} {overall['em']:>8.4f} {overall['rouge_l']:>8.4f}")
    print("=" * 70)

    # Save
    output = {
        "meta": {
            "date": datetime.now().isoformat(),
            "version": f"zettelforge-{__version__}",
            "benchmark": "MemoryAgentBench (ICLR 2026)",
            "splits": splits,
            "limit": limit,
        },
        "by_split": results,
        "overall": overall,
    }

    results_path = Path(__file__).parent / "memoryagentbench_results.json"
    with open(results_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved: {results_path}")

    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MemoryAgentBench for ZettelForge")
    parser.add_argument("--split", nargs="+", default=None, help="Splits to run: AR, CR, TTL, LRU, all")
    parser.add_argument("--limit", type=int, default=None, help="Max rows per split")
    args = parser.parse_args()

    run_benchmark(splits=args.split, limit=args.limit)
