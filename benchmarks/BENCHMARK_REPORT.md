# ZettelForge Benchmark Report

**Version:** 1.5.0
**Date:** 2026-04-09
**Author:** Automated benchmark suite

---

## Executive Summary

ZettelForge v1.5.0 was evaluated across three benchmark suites measuring different capabilities:

| Benchmark | What it measures | Key result |
|-----------|-----------------|------------|
| **LOCOMO** (ACL 2024) | Conversational memory recall | 15.0% accuracy, 0.33 avg score |
| **CTIBench** (NeurIPS 2024) | CTI-domain entity extraction & attribution | Baseline established, methodology gaps identified |
| **RAGAS** | Retrieval quality metrics | 75.9% keyword presence, 17.7% string similarity |

**Latency:** All retrieval paths now complete in <1.5s p95 (down from 190s in v1.3.0).

---

## 1. LOCOMO Benchmark (Long-Context Conversational Memory)

**Source:** [LoCoMo](https://snap-research.github.io/locomo/) (ACL 2024)
**Dataset:** locomo10.json — 10 conversations, 5882 dialogue turns, 100 QA pairs
**Judge:** Keyword overlap (gold answer tokens vs retrieved context)
**Runs:** v1.3.0 (2026-04-09T09:22 UTC), v1.5.0 (2026-04-09T10:20 UTC)

### Results Comparison

| Category | v1.3.0 Accuracy | v1.5.0 Accuracy | Delta | v1.3.0 Avg Score | v1.5.0 Avg Score | Delta |
|----------|----------------|----------------|-------|-----------------|-----------------|-------|
| single-hop | 5.0% | **10.0%** | +5.0 | 0.20 | **0.25** | +0.05 |
| multi-hop | 0.0% | 0.0% | — | 0.00 | **0.15** | +0.15 |
| temporal | 0.0% | 0.0% | — | 0.125 | 0.12 | -0.005 |
| open-domain | 30.0% | 30.0% | — | 0.525 | **0.55** | +0.025 |
| adversarial | 35.0% | 35.0% | — | 0.575 | 0.57 | -0.005 |
| **Overall** | **14.0%** | **15.0%** | **+1.0** | **0.285** | **0.33** | **+0.045** |

### Latency Improvement

| Metric | v1.3.0 | v1.5.0 | Improvement |
|--------|--------|--------|-------------|
| p50 | 238ms | 344ms | +106ms (graph overhead) |
| **p95** | **189,931ms** | **1,305ms** | **99.3% reduction** |

The p95 collapse is the most significant improvement — broken graph stubs in v1.3.0 caused 190-second timeouts. The blended retriever completes all query types within 1.5s.

### LOCOMO Leaderboard Context

| System | Overall Accuracy |
|--------|-----------------|
| Mem0g | 68.5% |
| Mem0 | 66.9% |
| LangMem | 58.1% |
| OpenAI Memory | 52.9% |
| **ZettelForge 1.5.0** | **15.0%** |

### Why the gap remains

ZettelForge's entity extractor recognizes CTI entities (CVEs, APT groups, tools). LOCOMO uses conversational entities (person names, hobbies, life events). The knowledge graph is populated but graph traversal doesn't fire because no recognized entities appear in LOCOMO queries. See [Step 3 Roadmap](#step-3-roadmap-conversational-entity-extractor) below.

---

## 2. CTIBench Benchmark (NeurIPS 2024)

**Source:** [AI4Sec/cti-bench](https://huggingface.co/datasets/AI4Sec/cti-bench) (NeurIPS 2024)
**Paper:** [arxiv.org/abs/2406.07599](https://arxiv.org/abs/2406.07599)
**Run:** 2026-04-09T11:04 UTC

### CTI-ATE (ATT&CK Technique Extraction)

**Task:** Given a threat description, identify which MITRE ATT&CK technique IDs (T-codes) it describes.
**Samples:** 50 descriptions ingested and queried.
**Scoring:** Set-based Precision / Recall / F1 on predicted technique IDs vs ground truth.

| Metric | Score |
|--------|-------|
| Precision | 0.000 |
| Recall | 0.000 |
| F1 | 0.000 |
| p50 Latency | 111ms |

**Why F1=0:** The CTI-ATE descriptions are natural-language paraphrases of ATT&CK techniques — they do not contain the actual technique IDs (T1071, T1573, etc.). ZettelForge retrieves semantically similar descriptions but the scoring function (`extract_technique_ids`) looks for T-code regex patterns in the retrieved text, finding none.

**Fix required:** Ingest the MITRE ATT&CK technique database (technique ID → description mapping) alongside the CTIBench descriptions. Then retrieval can cross-reference descriptions with their T-codes. This is a benchmark methodology fix, not a ZettelForge deficiency.

### CTI-TAA (Threat Actor Attribution)

**Task:** Given a redacted threat report (actor name replaced with [PLACEHOLDER]), identify the threat actor.
**Samples:** 48 reports ingested and queried.

| Metric | Value |
|--------|-------|
| p50 Latency | 147ms |
| Unique predictions | 1 ("Cozy Bear" for all samples) |

**Why single prediction:** The query is identical for every sample ("Identify the threat actor referred to as [PLACEHOLDER]"). Since it contains no sample-specific entities, vector retrieval returns the same top-k notes regardless of which report was ingested. The actor extraction regex then finds "Cozy Bear" in one of those notes.

**Fix required:** Include a snippet of the specific report in the query (e.g., first 200 chars of the redacted text) so retrieval is context-specific. Ground truth scoring also requires `alias_dict.pickle` and `related_dict.pickle` from the [CTIBench GitHub repo](https://github.com/maveryin/cti-bench) for proper alias resolution.

### CTIBench Assessment

CTIBench is the right benchmark for ZettelForge's CTI domain, but the adapter needs two methodological fixes before scores are meaningful:
1. **ATE:** Cross-reference with ATT&CK technique database for ID resolution
2. **TAA:** Include report context in query for differentiated retrieval

These are adapter improvements, not ZettelForge core changes.

---

## 3. RAGAS Retrieval Quality Metrics

**Framework:** [RAGAS](https://docs.ragas.io/) v0.4.3
**Dataset:** LOCOMO (same as benchmark #1)
**Run:** 2026-04-09T11:46 UTC
**Scoring method:** Manual fallback (SequenceMatcher + keyword presence) — RAGAS native metrics require `rapidfuzz` which was not installed.

### Results

| Metric | Score | Interpretation |
|--------|-------|---------------|
| **Keyword Presence** | **75.9%** | 75.9% of gold answer keywords appear in retrieved context |
| **String Similarity** | **17.7%** | Low overlap between gold answer text and full retrieved context |
| p50 Latency | 320ms | Consistent with LOCOMO benchmark |

### Interpretation

The **keyword presence of 75.9%** is encouraging — it means ZettelForge's retrieval finds context containing most of the answer keywords. The low string similarity (17.7%) is expected because retrieved context is much longer than gold answers (full conversation sessions vs. short factual answers).

The gap between "keywords found in context" (75.9%) and "correct answer extracted" (15% LOCOMO accuracy) indicates the bottleneck is **answer extraction/synthesis**, not retrieval. The relevant information is in the retrieved context but the keyword-overlap judge can't match it because:
1. Gold answers are short ("Adoption agencies") but context is long conversation sessions
2. No synthesis step distills the context into a focused answer

### Recommendation

Adding the existing `SynthesisGenerator` to the benchmark pipeline (instead of returning raw context) would likely improve LOCOMO accuracy significantly, since the retrieval is already surfacing relevant content.

---

## Ingestion Performance

| Benchmark | Sessions | Duration | Rate | Causal Triples |
|-----------|----------|----------|------|---------------|
| LOCOMO v1.5.0 | 272 | 719s | 0.4/s | ~2,100 |
| CTI-ATE | 50 | 466s | 0.1/s | N/A |
| CTI-TAA | 48 | 678s | 0.1/s | N/A |
| RAGAS | 272 | 42s | 6.5/s | Skipped |

RAGAS ingestion was fast (6.5/s) because causal triple extraction was disabled for retrieval-only evaluation. Normal ingestion with causal extraction runs at ~0.4/s due to per-note LLM calls.

---

## What Changed in v1.5.0

| Feature | v1.3.0 | v1.5.0 |
|---------|--------|--------|
| Two-phase extraction pipeline | No | Yes (`remember_with_extraction()`) |
| Graph traversal in retrieval | Broken stubs | Working BFS + hop-distance scoring |
| Blended retrieval | No (vector-only or broken routing) | Yes (vector + graph, policy-weighted) |
| Intent-based policy weights | Logged but ignored | Applied via `BlendedRetriever` |
| p95 latency | 190s (pathological timeouts) | 1.3s |

---

## Roadmap

### Completed
- [x] Mem0-style two-phase extraction+update pipeline (PR #2)
- [x] Graph traversal retrieval with blended scoring (PR #3)
- [x] LOCOMO benchmark with v1.3.0 vs v1.5.0 comparison
- [x] CTIBench benchmark adapter (baseline established)
- [x] RAGAS retrieval quality metrics (baseline established)

### Next Steps

#### Step 3 Roadmap: Conversational Entity Extractor

**Problem:** ZettelForge's `EntityExtractor` only recognizes CTI entities (CVEs, APT groups, tools). LOCOMO queries contain conversational entities (person names, locations, events) that are invisible to graph traversal.

**What to change:**
1. Add NER patterns to `src/zettelforge/entity_indexer.py` — person names, locations, events, activities
2. Add entity types `person`, `location`, `event`, `activity` to the index
3. Update `src/zettelforge/note_constructor.py` to include conversational entities
4. Re-run LOCOMO benchmark

**Expected impact:** Single-hop 10% -> ~30%, Multi-hop 0% -> ~15-25%, Overall 15% -> ~25-30%

**Files to modify:**
- `src/zettelforge/entity_indexer.py:12-36` (EntityExtractor.PATTERNS)
- `src/zettelforge/note_constructor.py:23-37` (NoteConstructor.ENTITY_PATTERNS)
- `tests/test_basic.py` (add tests for new entity types)

#### Additional Improvements
- [ ] Fix CTIBench ATE adapter: ingest ATT&CK technique database for T-code cross-referencing
- [ ] Fix CTIBench TAA adapter: include report snippet in query for differentiated retrieval
- [ ] Install `rapidfuzz` and re-run RAGAS with native metrics (Faithfulness, ContextPrecision)
- [ ] Add `SynthesisGenerator` to LOCOMO benchmark pipeline for answer distillation
- [ ] Run LOCOMO with `--judge ollama` for LLM-based scoring

---

## Raw Data Files

| File | Description | Timestamp |
|------|-------------|-----------|
| `benchmarks/locomo_results_v1.3.0_baseline.json` | LOCOMO v1.3.0 baseline | 2026-04-09T09:22 UTC |
| `benchmarks/locomo_results.json` | LOCOMO v1.5.0 results | 2026-04-09T10:20 UTC |
| `benchmarks/ctibench_results.json` | CTIBench ATE+TAA results | 2026-04-09T11:04 UTC |
| `benchmarks/ragas_results.json` | RAGAS retrieval quality | 2026-04-09T11:46 UTC |
| `benchmarks/locomo_benchmark.py` | LOCOMO benchmark script | v1.5.0 |
| `benchmarks/ctibench_benchmark.py` | CTIBench adapter script | v1.5.0 |
| `benchmarks/ragas_benchmark.py` | RAGAS wrapper script | v1.5.0 |
