# P1 Features PRD -- ZettelForge

**Status**: Approved
**Author**: Alex (PM Agent) **Last Updated**: 2026-04-15 **Version**: 1.0
**Stakeholders**: Roland (Eng + Design + PM -- solo dev)

---

## Executive Summary

These five P1 features transform ZettelForge from a capable memory store into an
intelligence system that reasons about causality, evolves its own knowledge, and
does so on a crash-resistant storage layer. Collectively they close the three
research gaps identified in TE-009 (causal reasoning, memory evolution, persistence
semantics), fix the only benchmark scoring zero, and eliminate 8 crash windows per
`remember()` call by migrating from JSONL to SQLite. Each feature is independently
shippable and ordered by dependency: SQLite migration has no blockers, causal graph
and memory evolution can proceed in parallel after it, and persistence semantics
layers on top of the evolved schema.

---

## Dependency Map

```
SQLite Migration (no deps)
    |
    +---> Causal Graph (benefits from SQLite edge storage, but can use JSONL)
    |
    +---> Memory Evolution (needs note rewrite; easier on SQLite, works on JSONL)
    |
    +---> CTIBench ATE Fix (no deps -- pure recall parameter tuning)
    |
    +---> Persistence Semantics (needs schema field; ideally after SQLite migration)
```

Recommended build order: SQLite Migration -> Causal Graph -> Memory Evolution ->
Persistence Semantics -> CTIBench ATE Fix (can slot in anywhere as a 2-hour task).

---

## Feature 1: SQLite + LanceDB Storage Migration

### Problem

ZettelForge currently uses 5 independent file stores: `notes.jsonl`,
`kg_nodes.jsonl`, `kg_edges.jsonl`, the entity index (pickle/JSON), and LanceDB
for vectors. Each `remember()` call writes to multiple stores without
transactional guarantees, creating **8 crash windows** where a partial write
leaves stores inconsistent. The entity index uses a 5-second deferred flush; the
access counter uses a 60-second flush. Both lose data on crash.

Specific failures today:
- A note written to `notes.jsonl` but not yet indexed in LanceDB is invisible
  to `recall()`.
- KG edges appended to JSONL are duplicated on node update (append-only, no
  dedup on reload except in-memory cache).
- Entity index pickle corruption requires full rebuild.
- No way to detect or reconcile drift between stores.

### Solution

Replace all JSONL stores with a single SQLite database in WAL mode. LanceDB
stays for vector search (it is already embedded and crash-safe). A storage
adapter interface (Python ABC) lets JSONL remain as a legacy fallback and makes
the future PostgreSQL SaaS backend a drop-in.

**Tables:**

```sql
-- notes table (replaces notes.jsonl)
CREATE TABLE notes (
    id TEXT PRIMARY KEY,           -- note_YYYYMMDD_HHMMSS_xxxx
    version INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    evolved_from TEXT,
    evolved_by TEXT DEFAULT '[]',  -- JSON array of note IDs
    content_raw TEXT NOT NULL,
    content_source_type TEXT,
    content_source_ref TEXT,
    semantic_context TEXT,
    semantic_keywords TEXT,        -- JSON array
    semantic_tags TEXT,            -- JSON array
    semantic_entities TEXT,        -- JSON array
    embedding_model TEXT,
    embedding_hash TEXT,
    links_related TEXT DEFAULT '[]',
    links_superseded_by TEXT,
    links_supersedes TEXT DEFAULT '[]',
    links_causal_chain TEXT DEFAULT '[]',
    meta_access_count INTEGER DEFAULT 0,
    meta_last_accessed TEXT,
    meta_evolution_count INTEGER DEFAULT 0,
    meta_confidence REAL DEFAULT 1.0,
    meta_ttl INTEGER,
    meta_domain TEXT DEFAULT 'general',
    meta_tier TEXT DEFAULT 'B',
    meta_importance INTEGER DEFAULT 5,
    meta_tlp TEXT DEFAULT '',
    meta_stix_confidence INTEGER DEFAULT -1,
    meta_vuln TEXT                 -- JSON blob for VulnerabilityMeta
);

-- kg_nodes table (replaces kg_nodes.jsonl)
CREATE TABLE kg_nodes (
    node_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_value TEXT NOT NULL,
    properties TEXT DEFAULT '{}',  -- JSON
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(entity_type, entity_value)
);

-- kg_edges table (replaces kg_edges.jsonl)
CREATE TABLE kg_edges (
    edge_id TEXT PRIMARY KEY,
    from_node_id TEXT NOT NULL REFERENCES kg_nodes(node_id),
    to_node_id TEXT NOT NULL REFERENCES kg_nodes(node_id),
    relationship TEXT NOT NULL,
    properties TEXT DEFAULT '{}',  -- JSON
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(from_node_id, to_node_id, relationship)
);

-- entity_index table (replaces in-memory dict + pickle)
CREATE TABLE entity_index (
    entity_type TEXT NOT NULL,
    entity_value TEXT NOT NULL,
    note_id TEXT NOT NULL REFERENCES notes(id),
    created_at TEXT NOT NULL,
    PRIMARY KEY (entity_type, entity_value, note_id)
);

-- Indexes
CREATE INDEX idx_notes_domain ON notes(meta_domain);
CREATE INDEX idx_notes_superseded ON notes(links_superseded_by);
CREATE INDEX idx_kg_edges_from ON kg_edges(from_node_id);
CREATE INDEX idx_kg_edges_to ON kg_edges(to_node_id);
CREATE INDEX idx_kg_edges_rel ON kg_edges(relationship);
CREATE INDEX idx_entity_type_value ON entity_index(entity_type, entity_value);
CREATE INDEX idx_kg_nodes_type_value ON kg_nodes(entity_type, entity_value);
```

### User Stories

- As an agent operator, I want memory writes to be atomic so that a crash
  mid-`remember()` never leaves the system in an inconsistent state.
- As a developer, I want to switch between SQLite and JSONL backends via a
  single environment variable so that I can test or fall back without code changes.
- As a developer migrating an existing deployment, I want a one-command migration
  from JSONL to SQLite that validates completeness.

### Acceptance Criteria

- [ ] `ZETTELFORGE_BACKEND=sqlite` (new default) uses SQLite WAL mode for
      notes, KG nodes, KG edges, and entity index.
- [ ] `ZETTELFORGE_BACKEND=jsonl` falls back to current behavior, no regressions.
- [ ] Auto-detection: if `zettelforge.db` exists, use SQLite; if only JSONL
      files exist, use JSONL; if neither, create SQLite.
- [ ] `remember()` writes notes + KG edges + entity index in a single SQLite
      transaction. A `SIGKILL` mid-write leaves zero partial state.
- [ ] `access_count` and `last_accessed` are updated via SQL `UPDATE` (no
      deferred flush timer).
- [ ] Entity index queries (`get_note_ids`) use SQL index, not in-memory dict.
- [ ] Migration script: `python -m zettelforge migrate` reads all JSONL files,
      writes to SQLite, and prints a reconciliation report (counts per table,
      any notes missing from LanceDB).
- [ ] LanceDB dead metadata columns removed (`content`, `context`, `keywords`,
      `tags` -- verified never read in `VectorRetriever`).
- [ ] Superseded note vectors removed from LanceDB during `mark_note_superseded()`.
- [ ] `last_indexed_at` column in `notes` table; set when LanceDB upsert
      succeeds; `None` indicates drift.
- [ ] All 186+ existing tests pass on both backends.

### Technical Design

**Files to create:**

- `src/zettelforge/storage_abc.py` -- Abstract base class:
  ```python
  class StorageBackend(ABC):
      def write_note(self, note: MemoryNote) -> None: ...
      def get_note_by_id(self, note_id: str) -> Optional[MemoryNote]: ...
      def rewrite_note(self, note: MemoryNote) -> None: ...
      def count_notes(self) -> int: ...
      def mark_access(self, note_id: str, count: int, ts: str) -> None: ...
  ```
- `src/zettelforge/storage_sqlite.py` -- SQLite implementation.
- `src/zettelforge/storage_jsonl.py` -- Wraps existing `MemoryStore` to conform
  to ABC (thin adapter).
- `src/zettelforge/migrate.py` -- JSONL-to-SQLite migration + reconciliation.

**Files to modify:**

- `src/zettelforge/memory_store.py` -- Factory function `get_storage()` that
  reads `ZETTELFORGE_BACKEND` and returns the correct backend.
- `src/zettelforge/memory_manager.py` -- Replace `self.store = MemoryStore()`
  with `self.store = get_storage()`.
- `src/zettelforge/knowledge_graph.py` -- `KnowledgeGraph.__init__()` takes a
  `StorageBackend` or creates its own SQLite connection from the same DB file.
  All `_append_jsonl` calls become SQL inserts.
- `src/zettelforge/entity_indexer.py` -- `EntityIndexer` reads/writes from
  `entity_index` table instead of in-memory dict + pickle.
- `src/zettelforge/vector_retriever.py` -- Confirm dead LanceDB columns are
  never read (they are not -- verified in code review). Remove them from
  LanceDB schema on next index.

**Key implementation detail:** The SQLite DB file lives at
`{data_dir}/zettelforge.db`. KG, notes, and entity index share the same
connection with WAL mode enabled on first open:
```python
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA synchronous=NORMAL")
```

### Dependencies

- None. This is the foundation for other P1 features.
- Blocks: nothing strictly, but Causal Graph and Memory Evolution both benefit
  from transactional writes.

### Effort Estimate

**5-6 days** for a single developer.
- Day 1: Storage ABC + SQLite schema + basic CRUD.
- Day 2: Wire `MemoryManager`, `KnowledgeGraph`, `EntityIndexer` to ABC.
- Day 3: Migration script + reconciliation logic.
- Day 4: LanceDB cleanup (dead columns, supersession vector removal, `last_indexed_at`).
- Day 5: Test suite on both backends, auto-detection logic.
- Day 6 (buffer): Edge cases, CI, documentation.

### Success Metrics

- Zero crash-window writes: `remember()` is a single transaction.
- Entity index queries complete in <1ms (SQL index vs. 5s deferred flush).
- Migration script converts a 1000-note JSONL store in <10 seconds.
- All 186+ tests green on SQLite backend.
- LanceDB index size decreases after dead column removal.

---

## Feature 2: Causal Graph

### Problem

ZettelForge already extracts causal triples via LLM in the background enrichment
worker (`NoteConstructor.extract_causal_triples()`), and the intent classifier
already recognizes `CAUSAL` intent for "why" queries. But there is a critical
gap: **causal triples are stored as generic KG edges with no explicit causal
typing**, so the recall path cannot distinguish a causal edge (`APT28 --causes-->
data breach`) from a heuristic co-occurrence edge (`APT28 --USES_TOOL-->
Mimikatz`).

Current state:
- `_run_enrichment()` in `memory_manager.py:668-690` calls
  `extract_causal_triples()` and `store_causal_edges()`.
- `store_causal_edges()` in `note_constructor.py:165-199` stores triples via
  `kg.add_edge()` with `properties={"source": "llm_extraction"}`.
- The `relationship` field uses the causal relation directly (`causes`,
  `enables`, etc.) but these are indistinguishable from heuristic edges in
  traversal.
- The intent classifier detects `CAUSAL` intent but `recall()` does not route
  to causal-specific traversal -- it uses the same blended retrieval as every
  other intent.
- `Links.causal_chain` exists on `MemoryNote` but is never populated.

### Solution

1. **Explicit causal edge typing.** Add an `edge_type` field to KG edges with
   values `heuristic | causal | temporal`. All `store_causal_edges()` writes set
   `edge_type="causal"`. Heuristic edges from `_update_knowledge_graph()` set
   `edge_type="heuristic"`. Temporal edges set `edge_type="temporal"`.

2. **Causal traversal in recall.** When intent is `CAUSAL`, the graph retriever
   filters to `edge_type="causal"` edges only, then traverses the directed
   causal subgraph (BFS, max depth 3). This produces a causal chain:
   `A --causes--> B --enables--> C`.

3. **Provenance chain tracing.** Each causal edge stores `note_id` in its
   properties (already done). A new `Recall.provenance_chain(entity)` method
   walks causal edges and returns the chain of note IDs that established each
   link, enabling "show me the evidence" queries.

4. **Populate `Links.causal_chain`.** After causal triple extraction, update the
   source note's `links.causal_chain` with IDs of notes reachable via causal
   edges from its entities.

### User Stories

- As a CTI analyst agent, I want to ask "why did APT28 target the energy
  sector?" and get a causal chain (vulnerability -> exploit -> lateral movement
  -> data exfiltration) rather than a bag of related notes.
- As an incident responder agent, I want to trace the provenance of a causal
  claim back to the specific notes that established each link.
- As a developer, I want causal edges to be explicitly typed so I can query,
  filter, and visualize them separately from heuristic co-occurrence edges.

### Acceptance Criteria

- [ ] KG edges have an `edge_type` field: `heuristic`, `causal`, or `temporal`.
- [ ] All edges created in `_update_knowledge_graph()` have `edge_type="heuristic"`.
- [ ] All edges created in `store_causal_edges()` have `edge_type="causal"`.
- [ ] All edges created in `add_temporal_edge()` have `edge_type="temporal"`.
- [ ] `KnowledgeGraph.get_neighbors()` accepts optional `edge_type` filter.
- [ ] `GraphRetriever.retrieve_note_ids()` accepts optional `edge_type` filter.
- [ ] When `recall()` classifies intent as `CAUSAL`, graph retrieval filters
      to `edge_type="causal"` and traverses max depth 3.
- [ ] `MemoryManager.provenance_chain(entity_type, entity_value)` returns a list
      of `{subject, relation, object, note_id, created_at}` dicts tracing the
      causal path from the given entity.
- [ ] `Links.causal_chain` is populated on notes that have outgoing causal edges.
- [ ] Test: store 3 notes establishing `A --causes--> B --enables--> C`, then
      `recall("why does C happen?")` returns notes in causal order with the
      chain visible.
- [ ] Existing heuristic edges in KG (from pre-migration data) default to
      `edge_type="heuristic"` -- migration backfill or load-time default.

### Technical Design

**Files to modify:**

- `src/zettelforge/knowledge_graph.py`:
  - `add_edge()`: Add `edge_type: str = "heuristic"` parameter. Store in edge
    dict and persist.
  - `add_temporal_edge()`: Pass `edge_type="temporal"`.
  - `get_neighbors()`: Add `edge_type: Optional[str] = None` filter.
  - `_load_all()`: Default missing `edge_type` to `"heuristic"` for existing data.
  - New method: `get_causal_chain(entity_type, entity_value, max_depth=3)` --
    BFS over `edge_type="causal"` edges, returns ordered path.

- `src/zettelforge/note_constructor.py`:
  - `store_causal_edges()`: Pass `edge_type="causal"` to `kg.add_edge()`.

- `src/zettelforge/memory_manager.py`:
  - `_update_knowledge_graph()`: Pass `edge_type="heuristic"` to all
    `kg.add_edge()` calls (13 call sites).
  - `_run_enrichment()`: After storing causal edges, update source note's
    `links.causal_chain` with entity node IDs reachable via causal edges.
  - `recall()`: When `intent == QueryIntent.CAUSAL`, pass
    `edge_type="causal"` to `GraphRetriever`.
  - New method: `provenance_chain(entity_type, entity_value)`.

- `src/zettelforge/graph_retriever.py`:
  - `retrieve_note_ids()`: Accept and forward `edge_type` filter.

- `src/zettelforge/blended_retriever.py`:
  - When causal intent, increase graph weight to 0.7 (currently policy-driven,
    just update the causal policy weights).

**Data model change:** No schema change to `MemoryNote` -- `Links.causal_chain`
already exists. The change is in the KG edge dict which gains `edge_type`.

If SQLite migration lands first, the `kg_edges` table gets an `edge_type TEXT
DEFAULT 'heuristic'` column. If still on JSONL, the field is added to the edge
JSON dict.

### Dependencies

- Benefits from SQLite (can filter edges via SQL `WHERE edge_type='causal'`),
  but works on JSONL with in-memory filtering.
- Blocks: nothing directly.

### Effort Estimate

**3-4 days** for a single developer.
- Day 1: `edge_type` field on KG edges, update all write sites, load-time default.
- Day 2: Causal traversal method, `provenance_chain()`, `Links.causal_chain` population.
- Day 3: Intent-aware routing in `recall()`, graph retriever filtering.
- Day 4 (buffer): Tests, edge cases, existing data migration.

### Success Metrics

- "Why" queries return causal-chain-ordered results (not just vector similarity).
- `provenance_chain()` returns at least one link for notes with causal edges.
- No regression in non-causal recall quality (RAGAS scores stable).
- Causal edges are visually distinguishable in graph exports (by `edge_type` field).

---

## Feature 3: Memory Evolution (A-Mem)

### Problem

Notes in ZettelForge are **immutable once created**. When new CTI arrives that
updates, contradicts, or extends an existing note, the old note remains stale.
The only mechanism for change is supersession (full note replacement), which is
a blunt instrument -- it does not update the content of related notes.

Example: A note states "APT28 uses Sofacy malware." A new report reveals APT28
has shifted to HeadLace malware. The existing note is never updated. An agent
asking about APT28's current tooling gets stale information unless the new report
happens to rank higher in vector similarity.

The `MemoryNote` schema already has `evolved_from`, `evolved_by`, and
`increment_evolution()` -- these fields are present but never used in the write
path. The A-Mem paper (NeurIPS 2025) establishes this as the highest-value
capability for agentic memory systems.

### Solution

After creating a new note, find the top-k most similar existing notes and use an
LLM to decide whether each neighbor should be evolved (updated in-place) based
on the new information.

**Flow:**

```
remember(content) -> note_created
    |
    +-> evolve_neighbors(new_note)
         |
         +-> vector_search(new_note.embedding, k=5, exclude=new_note.id)
         |
         +-> for each neighbor:
         |     LLM prompt: "Given NEW information and EXISTING note,
         |                  should the existing note be updated?
         |                  Return: {action: 'evolve'|'keep', updated_content: ...}"
         |
         +-> if action == 'evolve':
               neighbor.content.raw = updated_content
               neighbor.updated_at = now
               neighbor.increment_evolution(new_note.id)
               neighbor.evolved_from = neighbor.id  (self-ref for lineage)
               re-embed neighbor
               persist updated neighbor
```

### User Stories

- As a CTI analyst agent, I want existing notes about APT28 to automatically
  incorporate new intelligence so that recall always returns the most current
  understanding, not stale snapshots.
- As a developer, I want memory evolution to be togglable via config so that I
  can disable it for benchmarking or resource-constrained environments.
- As an operator, I want to see which notes were evolved and by what trigger so
  that I can audit the chain of changes.

### Acceptance Criteria

- [ ] `MemoryManager.evolve_neighbors(new_note: MemoryNote, k: int = 5)` method
      exists and is called after note creation in `remember()`.
- [ ] Evolution is gated by config: `ZETTELFORGE_MEMORY_EVOLUTION=true` (default
      `true`). Can also be passed as `evolve_neighbors=False` to `remember()`.
- [ ] For each of the top-k neighbors (by cosine similarity, excluding the new
      note and superseded notes):
  - LLM is prompted with the new note content + neighbor content.
  - LLM returns `{action: "evolve" | "keep", updated_content: "...", reason: "..."}`.
  - If `action == "evolve"`, the neighbor is updated in-place.
- [ ] Updated neighbors have:
  - `updated_at` set to now.
  - `evolution_count` incremented.
  - `evolved_by` list includes the new note's ID.
  - `confidence` decayed to `min(current, 0.95)` (already in `increment_evolution()`).
  - Embedding re-computed from updated content.
  - LanceDB vector updated.
- [ ] Evolution runs on the background enrichment queue (not blocking `remember()`).
- [ ] Test: store a note "APT28 uses Sofacy", then store "APT28 has shifted to
      HeadLace malware in 2026". Verify the first note's content now mentions
      HeadLace and `evolution_count == 1`.
- [ ] Evolution prompt includes a `keep` option -- not every neighbor should be
      updated. LLM must justify with `reason` field.
- [ ] Maximum evolution depth: a note evolved in this cycle is not eligible to
      trigger further evolution (no cascading).
- [ ] Evolution events are logged via structlog with note IDs, action, and reason.

### Technical Design

**Files to create:**

- `src/zettelforge/memory_evolution.py`:
  ```python
  class MemoryEvolver:
      def __init__(self, memory_manager: 'MemoryManager'):
          self.mm = memory_manager

      def evolve_neighbors(self, new_note: MemoryNote, k: int = 5) -> List[str]:
          """Find and evolve top-k neighbors. Returns IDs of evolved notes."""
          # 1. Vector search for neighbors
          neighbors = self.mm.retriever.retrieve(
              query=new_note.content.raw,
              k=k + 1,  # +1 to account for self-match
          )
          neighbors = [n for n in neighbors if n.id != new_note.id
                       and not n.links.superseded_by]

          evolved_ids = []
          for neighbor in neighbors[:k]:
              result = self._evaluate_evolution(new_note, neighbor)
              if result["action"] == "evolve":
                  self._apply_evolution(neighbor, new_note, result["updated_content"])
                  evolved_ids.append(neighbor.id)
          return evolved_ids
  ```

**Files to modify:**

- `src/zettelforge/memory_manager.py`:
  - Import `MemoryEvolver`.
  - In `remember()`, after enrichment queue dispatch, add evolution job to
    the same queue (new job type `_EvolutionJob`).
  - Add config check: `get_config().get("memory_evolution", True)`.

- `src/zettelforge/memory_store.py` (or `storage_abc.py` if SQLite lands first):
  - `rewrite_note()` must update LanceDB vector when content changes.
  - Ensure `_rewrite_note()` handles embedding update.

- `src/zettelforge/vector_retriever.py`:
  - Ensure `retrieve()` can accept a raw embedding vector (not just query string)
    for neighbor search. Currently takes a string query -- may need an overload or
    the evolver can use `self.mm.store.lance_table.search(vector)` directly.

**LLM prompt (stored in `memory_evolution.py`):**

```
You are a memory evolution agent. Given NEW information and an EXISTING memory
note, decide whether the existing note should be updated.

Rules:
- Only evolve if the new information ADDS, CORRECTS, or EXTENDS the existing note.
- Do NOT evolve if the new information is merely related but does not change
  the existing note's claims.
- Preserve the existing note's structure. Integrate new information naturally.
- If evolving, return the COMPLETE updated content (not a diff).

NEW INFORMATION:
{new_note_content}

EXISTING NOTE:
{neighbor_content}

Return JSON:
{
  "action": "evolve" or "keep",
  "reason": "one sentence explaining your decision",
  "updated_content": "full updated note content (only if action=evolve)"
}
```

### Dependencies

- Benefits from SQLite (atomic rewrite of note + re-index), but works on JSONL
  via existing `_rewrite_note()`.
- Requires LLM to be available (Ollama or cloud provider).
- Independent of Causal Graph.

### Effort Estimate

**3-4 days** for a single developer.
- Day 1: `MemoryEvolver` class, LLM prompt, `_evaluate_evolution()`.
- Day 2: `_apply_evolution()` with note rewrite, re-embedding, LanceDB update.
- Day 3: Integration into `remember()` enrichment queue, config toggle.
- Day 4 (buffer): Tests, cascade prevention, logging, edge cases.

### Success Metrics

- Notes within cosine similarity >0.7 of a new note are evaluated for evolution.
- At least 40% of evolution evaluations result in `keep` (proves the LLM is
  selective, not blindly updating).
- Evolved notes retain coherent content (manual spot-check of 10 evolved notes).
- No cascading evolution (depth capped at 1).
- Recall quality for updated entities improves (measure via CTIBench after
  evolution is enabled).

---

## Feature 4: CTIBench ATE Fix

### Problem

The CTIBench Attack Technique Extraction (ATE) benchmark scores **F1=0.0**. This
is caused by 4 compounding failures, not a fundamental architecture issue:

1. **Techniques not isolated in a queryable domain.** Attack patterns (MITRE
   T-codes) are stored as entities but there is no way to retrieve "all
   techniques mentioned in context X" without them being mixed into general
   recall results.
2. **k too small.** `recall()` defaults to `k=10`, but ATE benchmark questions
   reference reports containing 20-30 techniques. Top-10 misses most of them.
3. **Query framing wrong.** The benchmark wrapper likely sends the question
   verbatim as a recall query, but the question framing does not match how
   techniques are stored (entity index key vs. free-text description).
4. **No technique-specific retrieval path.** Unlike `recall_cve()` and
   `recall_actor()`, there is no `recall_technique()` convenience method.

Projected F1 after fixes: **0.30-0.40** (8-11x improvement).

### Solution

Three targeted fixes, each addressing a specific failure mode:

1. Add `recall_technique(technique_id_or_name, k)` method that searches the
   `attack_pattern` entity type in the entity index.
2. For ATE benchmark queries, increase `k` to 25 and use entity-augmented
   recall focused on `attack_pattern` entities.
3. Strip the benchmark question wrapper and query with the core entity/report
   reference directly.

### User Stories

- As a benchmark runner, I want the ATE benchmark to produce a non-zero F1
  score that reflects ZettelForge's actual technique extraction capability.
- As a CTI analyst agent, I want to ask "what techniques does APT28 use?" and
  get a comprehensive list, not just the top-10 vector-similar notes.

### Acceptance Criteria

- [ ] `MemoryManager.recall_technique(technique: str, k: int = 10)` method
      exists, searching both `attack_pattern` entity type and free-text
      matching for T-codes.
- [ ] ATE benchmark harness uses `k=25` for technique queries.
- [ ] ATE benchmark harness strips question wrapper text before querying
      (extract the core report/actor reference).
- [ ] ATE F1 score >= 0.25 on the standard CTIBench ATE dataset.
- [ ] No regression in other CTIBench subtask scores.
- [ ] RAGAS re-run with `--domain cti` produces updated baseline numbers.

### Technical Design

**Files to modify:**

- `src/zettelforge/memory_manager.py`:
  - Add `recall_technique()` method (pattern matches `recall_cve()`,
    `recall_actor()`, `recall_tool()`):
    ```python
    def recall_technique(self, technique: str, k: int = 10) -> List[MemoryNote]:
        """Fast lookup by MITRE technique ID or name."""
        results = self.recall_entity("attack_pattern", technique.upper(), k)
        if len(results) < k:
            # Also search by lowercase name
            more = self.recall_entity("attack_pattern", technique.lower(), k - len(results))
            seen = {n.id for n in results}
            results.extend(n for n in more if n.id not in seen)
        return results
    ```

- Benchmark harness (location TBD -- likely `benchmarks/ctibench/` or `tests/benchmarks/`):
  - Increase `k` parameter for ATE queries.
  - Add query preprocessing: strip "Based on the report..." wrappers, extract
    the entity reference.
  - Use `recall_technique()` for technique-specific questions.

- `src/zettelforge/web.py` or MCP tool definitions (if ATE is exposed via MCP):
  - Expose `recall_technique` as an MCP tool.

### Dependencies

- None. This is purely a recall path fix + benchmark harness tuning.
- Can be done in parallel with any other P1 feature.

### Effort Estimate

**0.5 days** (~2.25 hours as estimated in TODO.md).
- 1 hour: `recall_technique()` method + tests.
- 0.5 hours: Benchmark harness query preprocessing.
- 0.75 hours: Run benchmark, verify F1, update baseline numbers.

### Success Metrics

- ATE F1 >= 0.25 (target 0.30-0.40).
- Other CTIBench subtask scores unchanged or improved.
- RAGAS baseline updated with `--domain cti` scores.

---

## Feature 5: Persistence Semantics

### Problem

All notes in ZettelForge are treated identically regardless of their nature.
An IOC (IP address linked to malware C2) and an ephemeral reasoning step ("I
checked VirusTotal and found 3 detections") have the same update rules, the
same decay behavior, and the same recall priority. This leads to:

- **IOCs decaying** when they should be permanent reference data.
- **Ephemeral reasoning context** cluttering recall results long after it is
  irrelevant.
- **Synthesized insights** being updated without evidence gates, diluting their
  confidence over time.
- **Analyst session notes** persisting indefinitely when they should fade from
  recall as they age.

The `Metadata.tier` field (`A`/`B`/`C`) partially addresses this with
epistemic tiers for consolidation, but it does not encode update rules or
decay behavior. The Knowledge Layer paper (arXiv:2604.11364) formalizes this
as four persistence classes.

### Solution

Add a `persistence_semantics` field to `MemoryNote.Metadata` with four values,
each encoding distinct lifecycle rules:

| Semantic | Examples | TTL | Update Rule | Decay |
|----------|----------|-----|-------------|-------|
| `knowledge` | IOCs, TTP definitions, CVE records | Indefinite | Strict: only update with higher-confidence source | None |
| `memory` | Analyst session notes, conversation context | 30-90 days default | Soft: any new information can update | Ebbinghaus-style (access resets) |
| `wisdom` | Synthesized insights, trend analyses | Indefinite | Evidence-gated: requires 2+ supporting notes | None, but confidence decays if supporting notes are superseded |
| `intelligence` | Reasoning context, intermediate steps | 7 days default | None (append-only, never evolve) | Hard TTL, auto-expire |

### User Stories

- As a CTI analyst agent, I want IOC notes to persist indefinitely and resist
  casual updates so that I can trust their accuracy.
- As an operator, I want ephemeral reasoning steps to auto-expire after 7 days
  so that they do not clutter future recall results.
- As a synthesis engine, I want insight notes to require evidence from multiple
  sources before being updated so that synthesized knowledge remains reliable.

### Acceptance Criteria

- [ ] `Metadata.persistence_semantics` field added to `MemoryNote` with type
      `Literal["knowledge", "memory", "wisdom", "intelligence"]`, default `"memory"`.
- [ ] `NoteConstructor.construct()` infers `persistence_semantics` from
      `source_type` and `domain`:
  - `source_type="ingestion"` + `domain="cti"` -> `"knowledge"`
  - `source_type="conversation"` -> `"memory"`
  - `source_type="synthesis"` -> `"wisdom"`
  - `source_type="task_output"` with `domain != "cti"` -> `"intelligence"`
  - Explicit override via parameter always wins.
- [ ] `knowledge` notes: `ttl=None`, evolution requires
      `new_note.metadata.confidence >= existing.metadata.confidence`.
- [ ] `memory` notes: `ttl=90` (default, configurable), access resets decay
      timer. Notes not accessed within TTL are excluded from `recall()`.
- [ ] `wisdom` notes: `ttl=None`, evolution requires `evolved_by` list to
      contain >= 2 distinct note IDs (evidence gate).
- [ ] `intelligence` notes: `ttl=7` (default, configurable), never evolved
      (skipped by `evolve_neighbors()`), excluded from recall after expiry.
- [ ] `recall()` filters out expired notes (where `created_at + ttl < now`
      and `last_accessed + ttl < now` for memory-type).
- [ ] Consolidation layer (`consolidation.py`) respects persistence semantics:
  - `knowledge` notes are always TAN-eligible (stable knowledge).
  - `intelligence` notes are never promoted to TAN.
- [ ] Test: create notes of each type, advance time, verify TTL expiry and
      update rules.

### Technical Design

**Files to modify:**

- `src/zettelforge/note_schema.py`:
  - Add to `Metadata`:
    ```python
    persistence_semantics: str = "memory"  # knowledge | memory | wisdom | intelligence
    ```

- `src/zettelforge/note_constructor.py`:
  - `construct()`: Infer `persistence_semantics` from `source_type` + `domain`.
    Add `persistence_semantics: Optional[str] = None` parameter for explicit
    override.

- `src/zettelforge/memory_evolution.py` (from Feature 3):
  - `_evaluate_evolution()`: Check neighbor's `persistence_semantics`:
    - `knowledge`: only evolve if new note confidence >= neighbor confidence.
    - `wisdom`: only evolve if neighbor already has >= 2 entries in `evolved_by`.
    - `intelligence`: skip entirely.
    - `memory`: evolve freely (current behavior).

- `src/zettelforge/memory_manager.py`:
  - `recall()`: Add TTL filter before returning results:
    ```python
    if note.metadata.persistence_semantics == "intelligence":
        if _is_expired(note, default_ttl=7): continue
    elif note.metadata.persistence_semantics == "memory":
        if _is_expired(note, default_ttl=90): continue
    ```

- `src/zettelforge/consolidation.py`:
  - `_should_promote_to_tan()`: Check `persistence_semantics`:
    - `knowledge` -> always eligible.
    - `intelligence` -> never eligible.

- SQLite migration (if landed): Add `meta_persistence_semantics TEXT DEFAULT
  'memory'` column to `notes` table.

### Dependencies

- **Soft dependency on Memory Evolution (Feature 3).** Persistence semantics
  define evolution rules, but the field can be added and the inference logic
  shipped before evolution is implemented. The evolution guard logic ships with
  Feature 3.
- No hard blockers.

### Effort Estimate

**2-3 days** for a single developer.
- Day 1: Schema field, inference logic in `NoteConstructor`, TTL expiry filter
  in `recall()`.
- Day 2: Consolidation integration, evolution guard rules (or stubs if Feature 3
  not yet landed).
- Day 3 (buffer): Tests for each persistence type, edge cases around TTL reset
  on access.

### Success Metrics

- 100% of new notes have a non-empty `persistence_semantics` value.
- `intelligence`-type notes are absent from recall results after 7 days.
- `knowledge`-type notes are never downgraded or expired.
- `wisdom`-type notes with only 1 supporting source resist evolution attempts.
- Recall result quality improves as ephemeral notes are filtered (measure via
  RAGAS context precision).

---

## Appendix: Total Effort and Sequencing

| Feature | Effort (days) | Dependencies | Parallel-safe with |
|---------|---------------|--------------|---------------------|
| SQLite Migration | 5-6 | None | CTIBench ATE Fix |
| Causal Graph | 3-4 | Benefits from SQLite | Memory Evolution |
| Memory Evolution | 3-4 | Benefits from SQLite | Causal Graph |
| CTIBench ATE Fix | 0.5 | None | Everything |
| Persistence Semantics | 2-3 | Soft dep on Evolution | Causal Graph |

**Total: 14-17.5 developer-days** (~3 weeks at sustainable pace).

**Recommended sequence:**
1. CTIBench ATE Fix (2 hours, immediate credibility win for benchmarks)
2. SQLite Migration (foundation, eliminates crash risk)
3. Causal Graph + Memory Evolution (parallel, both benefit from SQLite)
4. Persistence Semantics (layers on top of evolution rules)
