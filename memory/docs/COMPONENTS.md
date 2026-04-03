# A-MEM Component Registry

**Version:** 1.3  
**Date:** 2026-04-02  
**Project:** A-MEM (Agentic Memory)

---

## Core Components

### 1. MemoryManager

| Property | Value |
|----------|-------|
| **Location** | `memory/memory_manager.py` |
| **Purpose** | Main interface for primary agent memory operations |
| **Key Methods** | `remember()`, `recall()`, `recall_cve()`, `recall_actor()`, `get_snapshot()` |
| **Dependencies** | MemoryStore, NoteConstructor, LinkGenerator, MemoryEvolver, VectorRetriever, EntityIndexer, AliasResolver, ReasoningLogger |
| **Dependents** | Primary agent, memory_init, test_memory_system.py |
| **Configuration** | jsonl_path, lance_path, cold_path (filesystem paths) |
| **Error Behavior** | Graceful degradation if components unavailable; logging failures don't interrupt flow |
| **Test Coverage** | test_memory_system.py (33 tests, 100% passing) |

**Public Interface:**
```python
# Note creation
mm.remember(content, source_type, source_ref, domain) -> Tuple[MemoryNote, str]

# Entity recall
mm.recall_cve(cve_id, k, exclude_superseded) -> List[MemoryNote]
mm.recall_actor(actor_name, k, exclude_superseded) -> List[MemoryNote]
mm.recall_tool(tool_name, k, exclude_superseded) -> List[MemoryNote]
mm.recall_campaign(campaign_name, k, exclude_superseded) -> List[MemoryNote]
mm.recall_entity(entity_type, entity_value, k, exclude_superseded) -> List[MemoryNote]

# Semantic recall
mm.recall(query, domain, k, include_links, exclude_superseded) -> List[MemoryNote]

# Session management
mm.get_snapshot() -> List[MemoryNote]
mm.get_stats() -> Dict

# Maintenance
mm.rebuild_entity_index() -> Dict
mm.archive_low_confidence_notes() -> Dict
mm.get_archived_notes() -> List[str]
```

---

### 2. MemoryStore

| Property | Value |
|----------|-------|
| **Location** | `memory/memory_store.py` |
| **Purpose** | JSONL-based memory note storage with LanceDB vector indexing |
| **Key Methods** | `write_note()`, `read_all_notes()`, `iterate_notes()`, `get_note_by_id()`, `count_notes()` |
| **Dependencies** | note_schema (MemoryNote) |
| **Dependents** | MemoryManager, LinkGenerator, MemoryEvolver, VectorRetriever |
| **Configuration** | jsonl_path, lance_path |
| **Error Behavior** | Graceful handling of missing files, JSON parse errors logged and skipped |
| **Test Coverage** | Via MemoryManager tests |

**Storage Format:**
- Primary: `notes.jsonl` (append-only)
- Vector: `vector_memory.lance/memories.lance` (LanceDB)

---

### 3. EntityIndexer

| Property | Value |
|----------|-------|
| **Location** | `memory/entity_indexer.py` |
| **Purpose** | Fast lookup by known entity (CVE, actor, tool, campaign, sector) |
| **Key Methods** | `build()`, `add_note()`, `get_note_ids()`, `has_entity()`, `stats()` |
| **Dependencies** | EntityExtractor, AliasResolver |
| **Dependents** | MemoryManager, LinkGenerator, MemoryEvolver |
| **Configuration** | jsonl_path, index_path (entity_index.json) |
| **Error Behavior** | Returns empty results if index not found; rebuilds automatically on build() |
| **Test Coverage** | test_memory_system.py Phase 1 (14 tests) |

**Extractors:**
- **CVE**: Pattern `CVE-\d{4}-\d{4,}` (case-insensitive)
- **Actor**: ~50 known actors via regex pattern matching
- **Tool**: ~30 known tools via regex pattern matching
- **Campaign**: Pattern `Operation\s+\w+`
- **Sectors**: Keyword matching (DIB, Healthcare, MSSP, OT, Federal, etc.)

---

### 4. EntityExtractor

| Property | Value |
|----------|-------|
| **Location** | `memory/entity_indexer.py` |
| **Purpose** | Extract entities from raw text content |
| **Key Methods** | `extract_all()` → Dict with cves, actors, tools, campaigns, sectors |
| **Dependencies** | AliasResolver |
| **Dependents** | EntityIndexer |
| **Error Behavior** | Returns empty list for unrecognized entities; graceful degradation |

**Known Entities:**
- **Actors**: Volt Typhoon, MuddyWater, APT28/29/41, Lazarus, Fin7, Phosphorus, Lockbit, etc.
- **Tools**: Cobalt Strike, Metasploit, Mimikatz, BloodHound, Caldera, Sliver, etc.
- **Campaigns**: Operation NoVoice, Operation Clandestine Fox, etc.
- **Sectors**: DIB, Healthcare, MSSP, OT, Federal, Finance, Retail, Telecom

---

### 5. LinkGenerator

| Property | Value |
|----------|-------|
| **Location** | `memory/link_generator.py` |
| **Purpose** | Generate conceptual links between memory notes |
| **Key Methods** | `generate_links()`, `_get_entity_correlated_notes()`, `update_note_links()` |
| **Dependencies** | Ollama (LLM), EntityIndexer |
| **Dependents** | MemoryManager |
| **Configuration** | llm_model (qwen2.5:3b), similarity_threshold (0.65) |
| **Error Behavior** | Returns empty links on LLM failure; logs error for debugging |
| **Test Coverage** | test_memory_system.py Phase 2 (5 tests) |

**Relationship Types:**
- SUPPORTS: Corroborates information
- CONTRADICTS: Conflicts information
- EXTENDS: Adds nuance
- CAUSES: Causal relationship
- RELATED: Topically connected

---

### 6. MemoryEvolver

| Property | Value |
|----------|-------|
| **Location** | `memory/memory_evolver.py` |
| **Purpose** | Execute memory evolution with versioning and archival |
| **Key Methods** | `run_evolution_cycle()`, `evolve_note()`, `_archive_version()` |
| **Dependencies** | MemoryStore, EvolutionDecider, ReasoningLogger, concurrent.futures |
| **Dependents** | MemoryManager |
| **Configuration** | COLD_ARCHIVE path (/media/rolandpg/USB-HDD/archive/), MAX_EVOLUTION_CANDIDATES=10 |
| **Parallel Processing** | ThreadPoolExecutor with max 10 workers for assessment |
| **Performance** | ~0.5s for 10 candidates (parallel) vs ~3s sequential |
| **Error Behavior** | Archives skipped on path failure; evolution continues |
| **Test Coverage** | test_memory_system.py Phase 2 (5 tests) |

**Evolution Decisions:**
- NO_CHANGE: No update needed
- UPDATE_CONTEXT: Revise context summary
- UPDATE_TAGS: Update tags
- UPDATE_BOTH: Update both context and tags
- SUPERSEDE: Archive old note, update with new
- REJECT: Tier constraint prevented evolution

---

### 7. EvolutionDecider

| Property | Value |
|----------|-------|
| **Location** | `memory/memory_evolver.py` |
| **Purpose** | Decide if new note should trigger updates to existing memories |
| **Key Methods** | `assess(new_note, existing_note)` → Tuple(decision, reason) |
| **Dependencies** | Ollama (LLM) |
| **Dependents** | MemoryEvolver |
| **Configuration** | llm_model (qwen2.5:3b) |
| **Latency** | ~0.11s per assessment (vs ~10s with nemotron-3-nano) |
| **Error Behavior** | Returns NO_CHANGE on LLM failure |

**Epistemic Tier Rules (Phase 4.5):**
- Tier A (authoritative): Human/Tool facts. Cannot be superseded by B/C
- Tier B (operational): Agent reports. Cannot supersede A
- Tier C (support): Summaries. Never triggers supersession

---

### 8. VectorRetriever

| Property | Value |
|----------|-------|
| **Location** | `memory/vector_retriever.py` |
| **Purpose** | Retrieve notes by embedding similarity with domain filtering |
| **Key Methods** | `retrieve()`, `retrieve_by_embedding()`, `get_memory_context()` |
| **Dependencies** | VectorMemory (EmbeddingGenerator), MemoryStore |
| **Dependents** | MemoryManager, LinkGenerator |
| **Configuration** | similarity_threshold (0.30) |
| **Error Behavior** | Returns empty list if no candidates; gracefully handles missing vectors |

**Retrieval Process:**
1. Embed query using embedding model
2. Filter candidates by domain (if specified)
3. Calculate cosine similarity with all candidates
4. Filter by similarity threshold (0.30)
5. Sort by score, take top k
6. Expand via links (include linked notes)
7. Filter superseded notes (if exclude_superseded=True)

---

### 9. AliasResolver

| Property | Value |
|----------|-------|
| **Location** | `memory/alias_resolver.py` |
| **Purpose** | Resolve raw entity names to canonical forms |
| **Key Methods** | `resolve()`, `add_alias()`, `add_canonical_with_alias()`, `reload()`, `stats()` |
| **Dependencies** | None (self-contained) |
| **Dependents** | EntityIndexer, MemoryManager |
| **Configuration** | alias_map_dir (memory/alias_maps/) |
| **Error Behavior** | Raises ValueError on collisions; graceful degradation for unknown entities |

**Alias Maps:**
- `actors.json`: 18 canonical actors with aliases
- `tools.json`: Tool aliases (if exists)
- `campaigns.json`: Campaign aliases (if exists)

---

### 10. AliasManager

| Property | Value |
|----------|-------|
| **Location** | `memory/alias_manager.py` |
| **Purpose** | Track alias observations and auto-update alias maps (Phase 3.5) |
| **Key Methods** | `observe()`, `get_observation_count()`, `get_pending_aliases()`, `stats()` |
| **Dependencies** | AliasResolver |
| **Dependents** | MemoryManager |
| **Configuration** | observations_file, auto_threshold (3) |
| **Error Behavior** | Returns False on validation failures; continues operation |

**Auto-Update Mechanism:**
- Track (canonical, alias) observation pairs
- When count >= 3, auto-add alias to alias map
- Clear observations after successful auto-add
- Log to reasoning_log.jsonl

---

### 11. ReasoningLogger

| Property | Value |
|----------|-------|
| **Location** | `memory/reasoning_logger.py` |
| **Purpose** | Audit trail for evolution and link decisions (Phase 5.5) |
| **Key Methods** | `log_evolution()`, `log_link()`, `log_tier_assignment()`, `log_alias_added()`, `get_reasoning()`, `prune_old_entries()` |
| **Dependencies** | None (self-contained) |
| **Dependents** | MemoryManager, MemoryEvolver, AliasManager |
| **Configuration** | log_path, cold_path, retention_days (180) |
| **Error Behavior** | Fail silently if log file unavailable; events are non-critical |

**Event Types:**
- evolution_decision: Evolution assessment result
- link_created: Link generation event
- tier_assignment: Tier assignment on note save
- alias_added: Auto-added alias from observations

---

### 12. NoteConstructor

| Property | Value |
|----------|-------|
| **Location** | `memory/note_constructor.py` |
| **Purpose** | Construct structured memory notes from raw content |
| **Key Methods** | `enrich()`, `_assign_tier()`, `_generate_semantic()` |
| **Dependencies** | Ollama (LLM), EmbeddingGenerator |
| **Dependents** | MemoryManager |
| **Configuration** | llm_model (qwen2.5:3b) |
| **Latency** | ~1s for semantic enrichment (vs ~10s with nemotron-3-nano) |
| **Error Behavior** | Falls back to basic extraction on LLM failure |

**Tier Assignment Rules:**
- Tier A: human, tool, observation, ingestion, manual, briefing, advisory, cisa_advisory
- Tier B: conversation, subagent_output, task_output, cti_ingestion, agent
- Tier C: summary, synthesis, generated, review

---

### 13. EmbeddingGenerator

| Property | Value |
|----------|-------|
| **Location** | `embedding_utils.py` |
| **Purpose** | Generate embeddings for notes and queries |
| **Key Methods** | `embed()`, `embed_note_fields()`, `cosine_similarity()` |
| **Dependencies** | LLM Server or Ollama |
| **Dependents** | NoteConstructor, VectorRetriever, VectorMemory |
| **Configuration** | model (nomic-embed-text-v2-moe) |

---

## Supporting Files

| File | Purpose |
|------|---------|
| `note_schema.py` | MemoryNote Pydantic schema |
| `memory_init.py` | Global initialization helper |
| `test_memory_system.py` | 57-test test suite |
| `test_phase_3_5.py` | Alias resolution tests (7 tests) |
| `test_phase_4_5.py` | Epistemic tiering tests (10 tests) |
| `test_phase_5_5.py` | Reasoning memory tests (9 tests) |
| `test_phase_6.py` | Knowledge graph & IEP tests (36 tests) |
| `test_phase_7.py` | Synthesis layer tests (21 tests) |
| `test_integration.py` | Phase 6/7 integration tests (11 tests) |
| `test_performance.py` | Performance & scaling tests (6 tests) |
| `memory_plan_reviewer.py` | Weekly health check and iteration tracking |

---

## Phase 6 Components (Ontology & Knowledge Graph)

| Component | Location | Purpose |
|-----------|----------|---------|
| **OntologySchema** | `memory/ontology_schema.json` | Formal ontology definition with entity types, relationships, IEP 2.0 policy schema |
| **KnowledgeGraph** | `memory/knowledge_graph.py` | Graph storage with nodes, edges, policies - JSONL persistence |
| **OntologyValidator** | `memory/ontology_validator.py` | Schema validation, HASL validation, entity typing |
| **GraphRetriever** | `memory/graph_retriever.py` | Graph-based retrieval with IEP policy filtering |
| **IEPPolicy** | `memory/iep_policy.py` | IEP 2.0 policy management with temporal resolution |

## Phase 7 Components (Synthesis Layer)

| Component | Location | Purpose |
|-----------|----------|---------|
| **SynthesisGenerator** | `memory/synthesis_generator.py` | LLM-based answer synthesis with 4 output formats |
| **SynthesisRetriever** | `memory/synthesis_retriever.py` | Hybrid retrieval (vector + graph) for context |
| **SynthesisValidator** | `memory/synthesis_validator.py` | Response validation and quality scoring |

---

## Dependency Graph

---

## Dependency Graph

```
Primary Agent
     │
     ├─→ MemoryManager
     │    ├─→ MemoryStore
     │    ├─→ NoteConstructor
     │    ├─→ LinkGenerator → Ollama
     │    ├─→ MemoryEvolver
     │    ├─→ VectorRetriever
     │    ├─→ EntityIndexer → EntityExtractor
     │    ├─→ AliasResolver → alias_maps/*.json
     │    └─→ ReasoningLogger
     │
     ├─→ EmbeddingGenerator → Ollama
     │
     └─→ LanceDB (vector_memory.lance)
```

---

## Component Lifecycle

| Component | Initialization | Teardown |
|-----------|----------------|----------|
| MemoryManager | `get_memory_manager()` singleton | Global cleanup on exit |
| MemoryStore | Constructor (paths) | Append-only, no teardown |
| EntityIndexer | `load()` from disk | N/A |
| LinkGenerator | Constructor (model name) | N/A |
| MemoryEvolver | Constructor (store, evolver) | N/A |
| EvolutionDecider | Constructor (model name) | N/A |
| VectorRetriever | Constructor (threshold) | N/A |
| AliasResolver | Constructor (alias_map_dir) | Hot reload from disk |
| ReasoningLogger | Constructor (log_path) | Append-only, no teardown |
| NoteConstructor | Constructor (model name) | N/A |

---

## State Management

| Component | State Storage | Persistence |
|-----------|---------------|-------------|
| MemoryManager | In-memory (stats, initialized state) | Reloaded on restart |
| MemoryStore | `notes.jsonl` | Appended, append-only |
| EntityIndexer | `entity_index.json` | Rebuilt from notes on load |
| LinkGenerator | In-memory (model state) | N/A |
| MemoryEvolver | In-memory (model state) | N/A |
| EvolutionDecider | In-memory (model state) | N/A |
| VectorRetriever | In-memory (model state) | N/A |
| AliasResolver | `alias_maps/*.json` | Reloaded on init/reload |
| ReasoningLogger | `reasoning_log.jsonl` | Appended, append-only |
| NoteConstructor | In-memory (model state) | N/A |

---

## Testing Coverage

| Component | Test File | Tests | Status |
|-----------|-----------|-------|--------|
| MemoryManager | test_memory_system.py | 33 | ✅ 100% passing |
| EntityIndexer | test_memory_system.py Phase 1 | 14 | ✅ Passing |
| LinkGenerator | test_memory_system.py Phase 2 | 5 | ✅ Passing |
| MemoryEvolver | test_memory_system.py Phase 2 | 5 | ✅ Passing |
| AliasResolver | test_phase_3_5.py | 7 | ✅ Passing |
| EvolutionDecider | test_phase_4_5.py | 10 | ✅ Passing |
| ReasoningLogger | test_phase_5_5.py | 9 | ✅ Passing |

---

*End of Component Registry*
