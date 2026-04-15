# Graph Traversal Optimization — Design Document

**Date:** 2026-04-14
**Agent:** Data Architect
**Status:** Strategy 1 implemented. Strategies 2–5 queued for future sprints.

---

## The Key Insight

> The graph is computing the correct answer. The classifier is discarding it.

The knowledge graph contains the right relationships. The BFS traversal runs. The scores are valid. But for CTI relational queries — the exact queries that *should* use the graph — the intent classifier was assigning `FACTUAL` intent and setting `graph=0.0`. Every graph result was multiplied by zero before reaching the caller. The graph retriever was running and being silently discarded in the same pipeline.

---

## Root Cause: Four Compounding Failures

The graph traversal blackout was not a single bug. Four independent failures stacked to produce a total graph dropout on CTI relational queries.

**Failure 1 — RELATIONAL keyword list missed CTI query patterns.**
The classifier's RELATIONAL keyword set covers generic relationship phrasing (`who uses`, `related to`, `connected to`) but not the vocabulary CTI analysts actually use. Queries like "what infrastructure does APT28 use", "which campaigns target financial sector", "show relationships between Cobalt Strike and APT29", and "what indicators are associated with LockBit" contain no tokens from the RELATIONAL keyword list. They score zero for RELATIONAL.

**Failure 2 — CTI entity terms pushed queries into FACTUAL.**
The FACTUAL keyword list contains `apt`, `threat`, `malware`, `actor`, `tool`, `vulnerability`, `exploit`. A query like "what infrastructure does APT28 use" matches `apt` and `threat` for FACTUAL. Score: FACTUAL=2, RELATIONAL=0. Classification result: FACTUAL. This is the opposite of the correct routing.

**Failure 3 — FACTUAL policy set `graph=0.0`.**
Once a query is classified FACTUAL, its traversal policy applies `graph=0.0`. In the BlendedRetriever merge algorithm, graph results are multiplied by `policy["graph"]` before accumulation. At 0.0, every graph result contributes nothing to the blended score, regardless of BFS depth, hop count, or result count.

**Failure 4 — LLM fallback was never reached.**
The classification logic only invokes the LLM fallback when the best keyword score is less than 2. CTI relational queries typically score 2+ on FACTUAL due to the entity term overlap described in Failure 2. The LLM never saw these queries, so it had no opportunity to correct the misclassification.

The combined effect: any CTI query that mentions an actor, malware family, or infrastructure entity — which is most CTI queries — was routed to FACTUAL with `graph=0.0`, permanently suppressing graph traversal results.

---

## Strategy 1 — Intent Classifier Fix (Implemented)

**What changed:**

1. **FACTUAL policy: `graph` weight raised from `0.0` to `0.2`.**
   FACTUAL queries are entity lookups, and a graph weight of zero was too aggressive. Many factual CTI queries have a relational component (e.g., "what CVE does APT28 exploit" is factual *and* requires a graph hop). Setting `graph=0.2` allows graph results to contribute to FACTUAL blending without dominating it. Entity index weight (0.7) and vector weight (0.3) are unchanged.

2. **RELATIONAL keyword list expanded to cover CTI query patterns.**
   The following tokens were added to the RELATIONAL keyword intent list:

   | Added keyword | Example CTI query that now matches |
   |:--------------|:----------------------------------|
   | `what infrastructure` | "what infrastructure does APT28 use?" |
   | `which campaigns` | "which campaigns target financial sector?" |
   | `show relationships` | "show relationships between Cobalt Strike and APT29" |
   | `associated indicators` | "what indicators are associated with LockBit?" |
   | `relationships between` | "relationships between actor and malware" |
   | `targets` | "what does APT28 target?" |
   | `attributed to` | "what is this campaign attributed to?" |
   | `linked with` | "tools linked with FIN7" |
   | `campaigns by` | "campaigns by Sandworm" |
   | `infrastructure used` | "infrastructure used in Operation Aurora" |

**Why this is sufficient as a standalone fix:**
The RELATIONAL keyword expansion corrects the classification for the most common CTI relational query forms. Combined with the `graph=0.2` floor on FACTUAL, queries that still slip through to a FACTUAL classification will no longer have their graph results zeroed out entirely. The fix is conservative: it does not change the fundamental architecture, does not require retraining, and takes effect immediately on the next restart.

**Files changed:**
- `src/zettelforge/intent_classifier.py` — RELATIONAL keyword list, FACTUAL policy weight

---

## Strategy 2 — Alias Consolidation (Future Sprint)

**Problem:** TypeDB stores `APT28`, `Fancy Bear`, `Strontium`, and `Iron Twilight` as separate nodes. Queries for any one alias do not traverse edges connecting the others. The `get_aliases` inference function exists but is not called during BFS initialization. A query for "Fancy Bear infrastructure" starts BFS from the `Fancy Bear` node only, missing all edges on the canonical `APT28` node.

**Proposed fix:** Before BFS begins, resolve query entities through the alias inference chain. Collect all canonical and alias nodes for each entity. Seed BFS from the full alias-expanded entity set. Expected result: alias queries return the same graph results as canonical-name queries.

**Estimated impact:** +15–25% recall on queries using non-canonical actor names. High value for CTI workflows where aliases are the norm, not the exception.

---

## Strategy 3 — Relationship-Typed Traversal (Future Sprint)

**Problem:** BFS traversal is untyped. All edge types (uses, targets, attributed-to, indicates, mentioned-in) carry equal traversal weight. A query for "what does APT28 use?" traverses `uses`, `targets`, `mentioned-in`, and all other edge types equally. Results include notes reached via semantically irrelevant edge types, diluting precision.

**Proposed fix:** The intent classifier should extract relationship type hints from queries and pass them to the GraphRetriever as an allowed-edge-types filter. "Uses" queries filter to `uses` edges. "Targets" queries filter to `targets` edges. Untyped queries use all edges (current behavior). Edge-type filtering can be implemented as a predicate on the BFS neighbor expansion step without changing the BFS algorithm itself.

**Estimated impact:** +10–20% precision on relationship-specific queries. Reduces noise in top-k results.

---

## Strategy 4 — Bi-directional BFS (Future Sprint)

**Problem:** BFS starts from query entities and expands outward. For queries that specify both a source and a target entity (e.g., "how does APT28 relate to LockBit?"), one-directional BFS from APT28 may require traversing the full graph before reaching LockBit nodes. At `max_depth=2`, paths longer than 2 hops are invisible even if the connection exists.

**Proposed fix:** For queries where the entity extractor identifies 2+ entities, initialize BFS from both endpoints simultaneously and terminate when the frontiers meet. This halves the effective depth required to find a connecting path, allowing `max_depth=2` to surface connections that currently require `max_depth=4`.

**Estimated impact:** Surface inter-entity relationships that are currently invisible to the retriever. Estimated path discovery improvement of 2x for two-entity queries.

---

## Strategy 5 — Graph Densification (Future Sprint)

**Problem:** The knowledge graph is sparse. Notes are connected to entity nodes via `mentioned-in` edges, but note-to-note edges are thin. A note about APT28's use of Cobalt Strike and a note about Cobalt Strike C2 infrastructure are connected only through the shared `Cobalt Strike` entity node — not through a direct note-to-note edge encoding their relationship. BFS traversal through shared entity nodes adds 2 hops and loses path semantics.

**Proposed fix:** During `remember()`, after entity extraction, check whether newly stored notes share entities with existing notes. For high-overlap pairs (3+ shared entities, or 1+ shared entity with causal triple overlap), create explicit note-to-note edges in TypeDB with a `co-discusses` relation type. This densifies the graph without requiring manual curation, and BFS can traverse note-to-note edges at 1 hop instead of 2.

**Estimated impact:** -1 average hop depth on multi-note traversals. Reduces note retrieval latency and increases recall depth within the same `max_depth` budget.

---

## Expected Benchmark Impact

| Strategy | Recall (RELATIONAL queries) | Precision | Latency | Status |
|:---------|:---------------------------|:----------|:--------|:-------|
| Baseline (before fix) | ~10% (graph zeroed) | N/A | Fast (graph discarded) | Pre-fix |
| Strategy 1: Classifier fix | ~60% | Unchanged | Unchanged | Implemented |
| + Strategy 2: Alias consolidation | ~75% | Unchanged | +2–5ms per query | Queued |
| + Strategy 3: Typed traversal | ~75% | +10–20% | Unchanged | Queued |
| + Strategy 4: Bi-directional BFS | ~85% | Unchanged | +3–8ms per query | Queued |
| + Strategy 5: Graph densification | ~90% | +5–10% | -1 hop average | Queued |

Recall figures are estimates based on the CTI-Specific Benchmark v2 corpus (queued, see `tasks/benchmark-strategy.md`). Baseline recall of ~10% reflects graph results that surface via vector overlap on the same notes, not from graph traversal itself.
