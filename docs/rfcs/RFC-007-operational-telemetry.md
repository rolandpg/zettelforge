---
title: "RFC-007: Operational Telemetry and Human Evaluation for Memory Effectiveness"
description: "Instrument ZettelForge to measure whether it's actually helping agents produce better analysis, via automated telemetry (debug-mode) and monthly human evaluation."
diataxis_type: "reference"
audience: "AI Engineer / Backend Developer"
tags: [rfc, telemetry, evaluation, observability, quality-assurance]
last_updated: "2026-04-23"
version: "2.5.0-proposed"
status: "DRAFT"
---

# RFC-007: Operational Telemetry and Human Evaluation for Memory Effectiveness

**Author:** Nexus (Roland Fleet)  
**Date:** 2026-04-23  
**Status:** DRAFT  
**Target Version:** 2.5.0  
**Depends on:** None (extends existing OCSF logging)  
**Related Work:** RFC-006 (ZettelForge Synthesis Benchmark Protocol)

---

## Summary

ZettelForge has synthetic benchmarks (CTIBench, RAGAS, LOCOMO) that test retrieval and synthesis in isolation. What we lack is **operational telemetry** — evidence that ZettelForge is actually helping agents (Vigil, Patton, Tamara) produce better CTI analysis in production.

This RFC proposes:
1. **Automated telemetry** — extend existing OCSF logging to capture per-query metrics (latency, recall precision, citation patterns, tier distribution)
2. **Auto-feedback** — infer note utility from citation patterns when debug logging is enabled
3. **Human evaluation** — monthly review of 20 random agent briefings with a structured rubric

After 1 month, we should be able to answer: "Is ZettelForge helping or hindering?"

---

## Problem Statement

**What we can say today:**
- ZettelForge ingests notes ✓
- ZettelForge retrieves notes ✓
- ZettelForge synthesizes answers ✓
- Synthetic benchmarks pass ✓

**What we cannot say:**
- Does Vigil produce better briefings with ZettelForge than without?
- Are the notes recalled actually relevant to the query?
- Does synthesis add value beyond raw note retrieval?
- Are critical notes being missed?
- Is synthesis hallucinating unsupported claims?

**The 2026-04-23 benchmark debacle taught us:** Don't claim effectiveness without measuring it properly.

---

## Existing Infrastructure (Leverage, Don't Replace)

ZettelForge already has OCSF-compliant structured logging (`zettelforge/ocsf.py`, `zettelforge/log.py`). Every `remember()`, `recall()`, and `synthesize()` call emits a JSON event:

```json
{
  "class_uid": 6002,
  "class_name": "API Activity",
  "activity_name": "recall",
  "duration_ms": 3067.61,
  "query": "What is Caroline's identity?",
  "result_count": 20,
  "request_id": "3869d91ee9d54546bc29d803cc74df87",
  "time": "2026-04-19T18:14:29.970342Z"
}
```

**Log files:**
- `~/.amem/logs/zettelforge.log` — all API activity (10MB rotate, 9 backups)
- `~/.amem/logs/audit.log` — security events only

**This RFC extends the existing OCSF events rather than creating a parallel system.**

---

## Specification

### Part 1: TelemetryCollector (New Module)

**File:** `src/zettelforge/telemetry.py`

```python
class TelemetryCollector:
    """Collects operational telemetry for recall/synthesis quality monitoring.
    
    When DEBUG logging is enabled, automatically captures detailed per-note
    metadata and citation-based feedback. When INFO or higher, only captures
    aggregated counts and basic timing.
    """
    
    def start_query(self, query: str, actor: str = None) -> str:
        """Begin tracking a query. Returns query_id for correlation."""
        
    def log_recall(
        self,
        query_id: str,
        results: List[MemoryNote],
        intent: str,
        vector_latency_ms: int = 0,
        graph_latency_ms: int = 0,
    ):
        """Log recall telemetry. Auto-captures per-note metadata in DEBUG mode."""
        
    def log_synthesis(
        self,
        query_id: str,
        result: Dict,
        synthesis_latency_ms: int = 0,
    ):
        """Log synthesis telemetry. Auto-captures citation tracking in DEBUG mode."""
        
    def log_feedback(
        self,
        query_id: str,
        note_id: str,
        utility: int,  # 1-5 scale
        agent: str = None,
    ):
        """Log explicit agent feedback about note utility."""
        
    def auto_feedback_from_synthesis(
        self,
        query_id: str,
        retrieved_notes: List[MemoryNote],
        synthesis_result: Dict,
    ):
        """Automatically infer feedback from citation patterns.
        
        DEBUG mode only:
        - Notes cited in synthesis → utility=4 (likely useful)
        - Notes retrieved but NOT cited → utility=2 (possibly irrelevant)
        """
```

**Data directory:** `~/.amem/telemetry/telemetry_YYYY-MM-DD.jsonl`

**Privacy:**
- Query text truncated to 200 chars (500 in DEBUG)
- No raw note content stored (only IDs and metadata)
- Feedback is explicit or inferred from citations
- All data stays local

---

### Part 2: MemoryManager Integration

**File:** `src/zettelforge/memory_manager.py`

**Changes:**
1. Import `get_telemetry()`
2. Initialize `self._telemetry` in `__init__`
3. In `recall()`:
   - Add optional `actor=None` kwarg
   - Call `self._telemetry.start_query(query, actor)` at entry
   - Time `self.retriever.retrieve()` and `graph_retriever.retrieve_note_ids()` separately via `perf_counter()` — narrow scope, excludes blend/rerank/augment (see PRD DD-2)
   - Call `self._telemetry.log_recall()` before return
   - Return a `RecallResult` (list subclass carrying `.query_id`) so callers opt into correlation without breaking the existing `for note in mm.recall(q):` pattern
4. In `synthesize()`:
   - Add optional `actor=None, query_id=None` kwargs
   - Agent-level call site is the correlation boundary: `rr = mm.recall(q); mm.synthesize(q, query_id=rr.query_id)`. When `query_id` is omitted, the synthesis event is captured uncorrelated.
   - Call `self._telemetry.log_synthesis()` before return
   - Call `self._telemetry.auto_feedback_from_synthesis()` (collector no-ops when DEBUG disabled)

**Key design decisions (see PRD for full rationale):**
- **Correlation is caller-opt-in, not implicit shared state.** Shared state (instance attribute or thread-local) is unsafe under the actual concurrency model (daemon enrichment thread, concurrent agents, potential asyncio callers). Explicit `query_id` kwarg is the only thread-safe option.
- **OCSF extension uses the `unmapped` object, not top-level `**details`.** OCSF v1.x class_uid 6002 does not permit arbitrary top-level custom fields. Use `zf_` prefix inside `unmapped` to reserve namespace.
- Vigil, Patton, and Tamara still get telemetry "for free" when `ZETTELFORGE_LOG_LEVEL=DEBUG` — they only need to pass the optional `query_id` if they want downstream analytics to join their recall and synthesis events.

---

### Part 3: Per-Query Metrics Captured

**In INFO mode (always):**

| Field | Type | Source |
|-------|------|--------|
| `event_type` | string | "recall" / "synthesis" |
| `timestamp` | float | epoch seconds |
| `query_id` | UUID | correlation key |
| `actor` | string | agent name (vigil, patton, tamara) |
| `result_count` | int | notes returned |
| `duration_ms` | int | total latency |

**In DEBUG mode (additional):**

| Field | Type | Why |
|-------|------|-----|
| `intent` | string | factual / temporal / relational / causal / exploratory |
| `tier_distribution` | dict | {"A": 5, "B": 3, "C": 2} |
| `vector_latency_ms` | int | Time for vector search |
| `graph_latency_ms` | int | Time for graph traversal |
| `synthesis_latency_ms` | int | Time for LLM synthesis |
| `total_latency_ms` | int | End-to-end time |
| `confidence` | float | Synthesis self-reported confidence |
| `sources_count` | int | How many notes cited |
| `notes` | list | Per-note metadata (id, rank, tier, source_type, domain) |
| `cited_notes` | list | Which specific notes were cited in synthesis |
| `feedback` | list | Auto-inferred utility scores (1-5) |

---

### Part 4: Aggregation and Dashboard

**File:** `scripts/telemetry_aggregator.py`

**Daily report format:**

```python
{
  "date": "2026-04-23",
  "total_queries": 47,
  "total_synthesis": 23,
  "avg_recall_latency_ms": 156,
  "avg_synthesis_latency_ms": 2847,
  "avg_confidence": 0.72,
  "notes_per_query": 8.3,
  "tier_distribution": {"A": 62, "B": 31, "C": 17},
  "feedback_count": 230,
  "avg_utility": 3.4,
  "top_utility_notes": ["note_abc", "note_def", ...],
  "unused_notes_count": 12,  # Notes never retrieved in period
}
```

**File:** `scripts/telemetry_dashboard.py` (Streamlit, optional)

Simple dashboard showing:
- Query volume over time
- Latency trends (p50/p95)
- Tier distribution
- Utility scores over time
- Unused notes warning

---

### Part 5: Human Evaluation (Monthly)

**What Patrick reviews:**
- 20 random Vigil briefings that used ZettelForge (sampled from telemetry log)

**Evaluation rubric (per briefing):**

| Question | Scale | What It Measures |
|----------|-------|------------------|
| Did ZettelForge recall relevant notes? | 1-5 | Recall precision |
| Did synthesis add value beyond raw notes? | 1-5 | Synthesis quality |
| Were any critical notes missing? | yes/no | Recall coverage |
| Did synthesis contain unsupported claims? | yes/no | Hallucination rate |
| Was the response faster with ZettelForge? | 1-5 | Latency perception |
| Overall: Would you trust this output? | 1-5 | Trust metric |

**Time commitment:** 2 hours/month

**Integration:** Human evaluations are appended to telemetry log as `event_type: "human_eval"` for correlation with automated metrics.

---

## Success Criteria

After 1 month of telemetry + 1 human evaluation cycle, we must be able to answer:

1. **Recall precision:** "% of recalled notes rated useful by agents or humans"
2. **Coverage:** "% of queries where critical info was NOT recalled"
3. **Synthesis quality:** "Average human-rated synthesis value (1-5)"
4. **Hallucination rate:** "% of briefings with unsupported claims"
5. **Latency:** "p50/p95 recall + synthesis latency"
6. **Operational health:** "Error rate, enrichment queue depth, unused notes"

**If metrics are poor, we know where to focus.** If recall precision is low → fix retrieval. If hallucination rate is high → fix synthesis. If coverage is poor → fix indexing.

---

## Implementation Plan

| Phase | What | Effort | Owner |
|-------|------|--------|-------|
| **1** | Implement `TelemetryCollector` + unit tests | 4h | AI Engineer |
| **2** | Integrate into `MemoryManager.recall()` and `.synthesize()` | 3h | AI Engineer |
| **3** | Build `telemetry_aggregator.py` | 2h | AI Engineer |
| **4** | Build `telemetry_dashboard.py` (Streamlit) | 3h | AI Engineer |
| **5** | Write human evaluation rubric + sampling script | 2h | AI Engineer |
| **6** | Document in `docs/telemetry.md` | 1h | AI Engineer |
| **7** | Pilot: collect 1 week of telemetry | passive | System |
| **8** | Patrick evaluates first 20 samples | 2h | Patrick |
| **9** | Analyze pilot, refine metrics | 2h | AI Engineer + Patrick |

**Total engineering:** ~17 hours  
**Total human time:** 4 hours (2h eval + 2h analysis)

---

## Open Questions

1. **Actor identity:** How does MemoryManager know which agent (vigil/patton/tamara) is calling? Options:
   - Pass `actor=` parameter to `recall()`/`synthesize()` (simplest)
   - Use thread-local context (more automatic, more magic)
   - Agent sets `mm._actor = "vigil"` before use (current pattern in some agents)

2. **Vector/graph latency:** Currently not measured separately. Add timing around `self.retriever.retrieve()` and `graph_retriever.retrieve_note_ids()` calls.

3. **Feedback scope:** Should `auto_feedback_from_synthesis()` only run for debug mode, or always? Proposal: debug mode only to avoid I/O overhead in production.

4. **Dashboard hosting:** Streamlit dashboard runs locally. Patrick accesses via `http://localhost:8501`. No external dependencies.

---

## Related Files

- `src/zettelforge/ocsf.py` — existing OCSF event emitters
- `src/zettelforge/log.py` — structlog configuration
- `src/zettelforge/memory_manager.py` — integration point
- `~/.amem/logs/zettelforge.log` — existing log destination
- RFC-006 — ZettelForge Synthesis Benchmark Protocol (complementary work)

---

*Prepared by Nexus | Roland Fleet | 2026-04-23*
