# LOCOMO Benchmark Comparison: v1.3.0 vs v1.5.0

**Date:** 2026-04-09
**Benchmark:** LoCoMo (Long-Context Conversational Memory), 20 samples per category, keyword-overlap judge
**Dataset:** locomo10.json (10 conversations, 5882 dialogue turns, 100 QA pairs)

---

## Results Summary

| Category | v1.3.0 Accuracy | v1.5.0 Accuracy | Delta | v1.3.0 Avg Score | v1.5.0 Avg Score | Delta |
|----------|----------------|----------------|-------|-----------------|-----------------|-------|
| single-hop | 5.0% | **10.0%** | +5.0 | 0.20 | **0.25** | +0.05 |
| multi-hop | 0.0% | 0.0% | 0.0 | 0.00 | **0.15** | +0.15 |
| temporal | 0.0% | 0.0% | 0.0 | 0.125 | 0.12 | -0.005 |
| open-domain | 30.0% | 30.0% | 0.0 | 0.525 | **0.55** | +0.025 |
| adversarial | 35.0% | 35.0% | 0.0 | 0.575 | 0.57 | -0.005 |
| **Overall** | **14.0%** | **15.0%** | **+1.0** | **0.285** | **0.33** | **+0.045** |

## Latency Comparison

| Category | v1.3.0 p50 | v1.5.0 p50 | v1.3.0 p95 | v1.5.0 p95 |
|----------|-----------|-----------|-----------|-----------|
| single-hop | 231ms | 341ms | 188,396ms | **1,375ms** |
| multi-hop | 188,538ms | **338ms** | 190,187ms | **397ms** |
| temporal | 234ms | 346ms | 190,150ms | **1,755ms** |
| open-domain | 221ms | 329ms | 191,462ms | **1,313ms** |
| adversarial | 234ms | 352ms | 278ms | 1,402ms |
| **Overall** | **238ms** | **344ms** | **189,931ms** | **1,305ms** |

## Ingestion

| Metric | v1.3.0 | v1.5.0 |
|--------|--------|--------|
| Sessions ingested | 272 | 272 |
| Errors | 0 | 0 |
| Duration | 678s | 719s |
| Rate | 0.4/s | 0.4/s |
| Causal triples extracted | N/A | ~2,100 |

---

## Analysis

### What improved

1. **Single-hop accuracy doubled** (5% -> 10%): The blended retrieval finds more relevant notes by combining vector similarity with graph-connected notes.

2. **Multi-hop avg_score jumped from 0.0 to 0.15**: Previously zero — the old recall() had a broken graph path that returned raw traverse paths without scoring. The new BlendedRetriever properly collects notes reachable via graph edges and scores them by hop distance. While no multi-hop questions scored a full 1.0 (exact match), 30% now score 0.5 (partial match), up from 0%.

3. **p95 latency collapsed from ~190s to ~1.3s (99.3% reduction)**: The old code had pathological p95 latencies because the broken temporal/relational paths fell through to expensive full-scan operations. The new blended retrieval runs both vector and graph in parallel and returns quickly.

4. **Overall avg_score improved 16%** (0.285 -> 0.33): More partial matches across all categories.

### What didn't improve

1. **Temporal accuracy still 0%**: The LOCOMO temporal questions require parsing natural language time references ("when did X happen?", "what changed after session 3?"). The current system doesn't extract temporal references from queries — the graph has temporal edges but they aren't queried with parsed timestamps.

2. **Multi-hop accuracy still 0%**: While avg_score improved (more partial matches), no multi-hop question scored a full 1.0. These questions require combining facts from 2+ different conversation sessions — the graph has edges between causal triples but the LOCOMO dataset's conversational entities (people, events, places) aren't the CTI entities (CVEs, actors, tools) that ZettelForge's entity extractor recognizes.

3. **Open-domain and adversarial unchanged**: These categories depend primarily on vector retrieval quality, which didn't change.

### Root causes for remaining gap vs Mem0 (66.9%)

1. **Entity extraction mismatch**: ZettelForge's entity extractor is CTI-focused (CVEs, APT groups, tools). The LOCOMO dataset is conversational (people's names, hobbies, life events). The graph gets populated with causal triples from LLM extraction, but the entity-based graph traversal doesn't fire because no CTI entities are found in the queries.

2. **No selective extraction**: The two-phase pipeline (`remember_with_extraction`) exists but the benchmark uses `remember()` directly. Running with `remember_with_extraction` would reduce noise but wouldn't change the entity mismatch.

3. **No temporal query parsing**: Need to extract dates/relative time references from queries and use `get_changes_since()` / `get_entity_timeline()`.

4. **Keyword judge limitations**: The keyword-overlap judge is strict. An LLM judge would likely score partial matches higher, improving reported numbers.

---

## LOCOMO Leaderboard Context

| System | Overall Accuracy | p95 Latency | Tokens/Query |
|--------|-----------------|-------------|--------------|
| Mem0g | 68.5% | 2.6s | ~4K |
| Mem0 | 66.9% | 1.4s | ~2K |
| LangMem | 58.1% | 60s | ~130 |
| OpenAI Memory | 52.9% | 0.9s | ~5K |
| **ZettelForge 1.5.0** | **15.0%** | **1.3s** | **N/A** |
| ZettelForge 1.3.0 | 14.0% | 190s | N/A |

---

## Recommended Next Steps (Priority Order)

1. **Add conversational entity extraction** — Extend EntityExtractor with person names, locations, events, hobbies from LOCOMO-style dialogues. This is the #1 blocker: the graph is rich with causal triples but entity-based traversal doesn't match query entities.

2. **Add temporal query parsing** — Extract date references ("after session 3", "when did", "last time") and use existing `get_entity_timeline()` / `get_changes_since()`.

3. **Use LLM judge** — Re-run with `--judge ollama` for more accurate scoring of partial matches.

4. **Run with remember_with_extraction()** — Modify benchmark to use the two-phase pipeline for ingestion, filtering low-importance filler turns.

5. **Add LLM synthesis** — Current benchmark returns raw retrieved context as the "answer". Adding a synthesis step (existing `SynthesisGenerator`) would produce focused answers that score better on keyword matching.

---

## Raw Data

- v1.3.0 baseline: `benchmarks/locomo_results_v1.3.0_baseline.json`
- v1.5.0 results: `benchmarks/locomo_results.json`
- Benchmark script: `benchmarks/locomo_benchmark.py`
- Benchmark run timestamp: 2026-04-09T10:20:40 UTC (v1.5.0)
- Baseline run timestamp: 2026-04-09T09:22:51 UTC (v1.3.0)
