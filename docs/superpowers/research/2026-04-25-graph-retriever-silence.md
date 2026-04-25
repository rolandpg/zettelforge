---
title: "Graph retriever silence — why `kg=0ms` on 98.7% of recalls"
status: ROOT CAUSE IDENTIFIED via static code trace; field verification pending next traffic run
author: "claude-code"
date: "2026-04-25"
scope: "Investigate task #42 — Vigil's 2026-04-24 live test showed `kg=0ms` on 148 of 150 recalls across factual / exploratory / relational / temporal intents"
data_sources:
  - "Vigil DEBUG telemetry 2026-04-24 23:44Z+ — 150 recalls, 2 with kg>0"
  - "src/zettelforge/memory_manager.py:580-624 (recall path)"
  - "src/zettelforge/graph_retriever.py:31-93 (retrieve_note_ids + _bfs_collect)"
  - "src/zettelforge/entity_indexer.py:69-130 (EntityExtractor regex set)"
---

# Graph retriever silence — root cause

## TL;DR

The graph retriever fires **only when the query string itself contains a regex-matchable CTI token** (CVE, APTNN, MITRE TID, IP/domain/hash). For natural-language queries that don't (e.g., *"recent Citrix exploitation"*, *"what tools did the actor use?"*, *"timeline of last week's incidents"*), the query-time extractor returns an empty entity dict, the BFS in `_bfs_collect` is never seeded, and `retrieve_note_ids` returns `[]` in microseconds — exactly the `kg=0ms` signal Vigil's telemetry recorded.

This is **not a bug in the graph retrieval path**. The graph code works correctly when given entities. The gap is upstream: the query-time entity extraction is regex-only, while *recall queries* are mostly written in natural language. The 2 of 150 calls that fired graph contained literal regex-matchable strings — likely the recall test that asked *"What malware did APT28 use?"* (matches the `apt28` regex pattern in `EntityExtractor.REGEX_PATTERNS["intrusion_set"]`).

## Code trace

### Step 1 — extract entities from the query (regex only)

`memory_manager.py` (the recall path) does:

```python
query_entities = self.indexer.extractor.extract_all(query, use_llm=False)
resolved = {etype: [resolver.resolve(etype, e) for e in elist]
            for etype, elist in query_entities.items()}
```

`extract_all(query, use_llm=False)` is the **regex-only** path of `EntityExtractor`. The full regex set (entity_indexer.py:32-69) covers:

- `cve` — `CVE-YYYY-NNNNN`
- `intrusion_set` — `apt`/`unc`/`ta`/`fin`/`temp` + digits
- `actor` — small handful of named groups (`lazarus`, `sandworm`, `volt typhoon`)
- `tool` — small handful (`cobalt strike`, `mimikatz`, `bloodhound`, etc.)
- `campaign` — `operation \w+`
- `attack_pattern` — `T\d{4}(?:\.\d{3})?`
- IOCs — `ipv4`, `domain`, `url`, `md5`, `sha1`, `sha256`, `email`

A natural-language query like *"recent Citrix exploitation"* matches **none** of these. `query_entities` returns `{}` and `resolved` is `{}`.

### Step 2 — graph retriever short-circuits on empty input

`graph_retriever.py:31-37`:

```python
def retrieve_note_ids(self, query_entities, max_depth=2) -> List[ScoredResult]:
    if not query_entities:
        return []
    ...
```

When `query_entities` is `{}`, `not query_entities` is `True` and we return `[]` immediately. No `kg.get_node` calls, no BFS, no walk-through. `_graph_latency_ms` measured around the call therefore lands at ~0ms because the function returns in microseconds.

### Step 3 — BlendedRetriever has nothing to merge

The blender at `memory_manager.py:626-633` falls back to vector results only. `recall()` returns vector-shaped output with no graph contribution. From the telemetry's perspective, `kg=0ms` is *correct* — the graph genuinely did no work — but it under-represents what we want, which is to **make the graph fire even on queries that the regex misses**.

## Why the 2 successful events fired

In the same 150-recall window, exactly 2 events showed `kg > 0`. The most likely explanation: those queries contained regex-matchable tokens. Test-suite traffic includes literal queries like *"What malware did APT28 use?"* — `apt28` matches the `intrusion_set` regex, the BFS seeds, and the graph walks the actual entity → note edges that `_index_in_lance` planted.

## What this means for `intent != factual`

Telemetry showed `kg=0ms` even on `relational` and `temporal` intents. We had assumed the intent classifier might gate the graph path; it doesn't. `recall()` calls the graph retriever unconditionally (`memory_manager.py:621-623`); the gate is purely whether the regex extractor produces seeds. So an `intent=relational` query like *"how is APT28 connected to PlugX?"* fires graph (matches `apt28` and `plugx` regexes) — but *"who's connected to last week's incident?"* doesn't (no regex tokens). The intent label is unrelated to the firing decision.

## Three possible fixes (ranked)

### A. **Run LLM-NER on the query** (preferred, smallest surface change)

`extract_all` already supports `use_llm=True`; the recall path explicitly passes `use_llm=False` for performance. Vigil's instrumentation now reports `vector_latency_ms` p95 ~500ms; an LLM-NER call adds ~200-500ms on a warm Ollama. That's tolerable for `relational`/`temporal`/`exploratory` intents that benefit most from graph signal.

**Implementation sketch**:
```python
# memory_manager.py:580
use_llm_for_query_entities = intent in ("relational", "temporal", "exploratory")
query_entities = self.indexer.extractor.extract_all(
    query, use_llm=use_llm_for_query_entities
)
```

Cost: only the queries that benefit pay the LLM hop. Factual queries with explicit CTI tokens still take the regex fast path. Risk: doubles the LLM-call surface area, so RFC-009 Phase 1 (LLM hardening) should land first.

### B. **Lookup entities from the corpus rather than the query**

If the query itself is sparse, walk the top-K vector neighbors first, then BFS from *their* entities. Same shape as the existing `causal` boost at `memory_manager.py:640-668`. This keeps the graph signal honest (anchored to retrieved notes) without an LLM hop.

**Implementation sketch**: after the vector retrieve, take the top 3 notes' `semantic.entities` field and feed them as `query_entities` to `retrieve_note_ids`. Cheap, no LLM dependency, and produces graph signal even for vague queries.

### C. **Tighten the blender contract — accept `query_entities=None`**

A no-op fallback that explicitly logs *"no graph signal — query entities empty"* so future operators see the gap in the telemetry stream rather than a silent 0. Doesn't fix the silence but makes it diagnosable. Free; can ship today as a one-line change to the OCSF event.

## Recommended path

Combine **B** and **C**. B fixes the symptom for most natural-language queries without any LLM dependency or new failure modes; C makes the remaining genuine "no graph signal" cases visible in telemetry instead of indistinguishable from the 0-result cases that existed before.

A is a v2.5.x experiment after RFC-009 Phase 1's LLM hardening lands — premature today because it doubles LLM-call surface against an unhardened provider.

## What this DOES NOT explain

- The 21-22% **zero-hit recall rate** that survived the Qwen → Nemotron LLM swap. Graph-silence is a *no-blend-signal* issue (graph contributes nothing to the score); zero-hit recall is a *vector-finds-nothing* issue. They're orthogonal failure modes. Task #40 still needs its own investigation — likely a vector-similarity-threshold or corpus-thinness question, not graph.

## Next step (verification before code change)

Pull a small sample (~20) of recalls from the post-cleanup test where `kg > 0` and confirm every one of them contains a regex-matchable token in the query string. If any of them don't, the BFS-seeded-by-vector-neighbors theory needs revising. The verification needs the per-recall `query` field, which DEBUG-level telemetry now captures — straightforward jq pull.

## Cross-references

- Task #42 in this session's task list (now closeable as "investigation complete; implementation tracked separately")
- Task #40 (zero-hit recall) — orthogonal; do not bundle
- RFC-009 Phase 1 (LLM hardening) — soft prerequisite for fix A
- `docs/superpowers/research/2026-04-25-v2.4.2-live-test-observations.md` (when it lands) for raw telemetry lineage
