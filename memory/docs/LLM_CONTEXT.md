# A-MEM LLM Context Document

**Version:** 1.3  
**Date:** 2026-04-02  
**Project:** A-MEM (Agentic Memory) - Roland Fleet  
**Target Tokens:** ~6,500 tokens (under 8,000 limit)

---

## 1. Project Overview

A-MEM is a self-organizing memory system for threat intelligence operations. It stores notes in JSONL format with vector embeddings for semantic search, while implementing entity indexing, deduplication, alias resolution, epistemic tiering, and cold archival. The system is built in Python using Ollama for LLM enrichment and LanceDB for vector storage. **Key principle:** Zero manual organization required - agents can retrieve information by entity type without search.

**Files:** Core Python files in `memory/` directory + 167 notes in `notes.jsonl`.

---

## 2. Directory Structure

| Directory/File | Purpose |
|----------------|---------|
| `memory/` | Core system files (memory_manager.py, note_schema.py, etc.) |
| `memory/docs/` | Documentation package (this file, PRD, architecture) |
| `memory/alias_maps/` | Entity alias mappings (actors.json, tools.json, campaigns.json) |
| `memory/notes/` | Topic-specific notes (PARA structure) |
| `vector_memory.lance/` | LanceDB vector store for cross-session recall |
| `notes.jsonl` | Main note storage (JSONL format, 167 notes) |
| `entity_index.json` | Entity → note ID mapping |
| `reasoning_log.jsonl` | Evolution/link decision audit trail |
| `dedup_log.jsonl` | Deduplication event log |
| `plan_iterations.jsonl` | PRD iteration history |
| `test_memory_system.py` | Main test suite (33 tests) |

---

## 3. Key Architectural Decisions

| Decision | Rationale |
|----------|-----------|
| **JSONL storage** | Simple append-only format, easy to audit and version |
| **LLM enrichment via Ollama** | Local LLM (nemotron-3-nano) for zero external API dependency |
| **Entity index (JSON)** | Fast typed lookup without semantic search overhead |
| **Zettelkasten-inspired** | Atomic notes with links, supports evolution and supersession |
| **Epistemic tiering** | Tier A (human) cannot be superseded by B/C (agent) |
| **Alias auto-update after 3 observations** | Automated canonical name discovery without manual curation |
| **Cold archive on evolution** | Preserves history while keeping active store clean |
| **Cross-session vector memory** | LanceDB stores memories accessible across all sessions |

---

## 4. Critical File Locations

| Component | File Path | Description |
|-----------|-----------|-------------|
| Memory Manager | `memory/memory_manager.py` | Main interface (remember, recall, etc.) |
| Note Schema | `memory/note_schema.py` | MemoryNote data model |
| Note Constructor | `memory/note_constructor.py` | LLM enrichment, tier assignment |
| Entity Indexer | `memory/entity_indexer.py` | Entity extraction and indexing |
| Link Generator | `memory/link_generator.py` | LLM-based link generation |
| Evolution | `memory/memory_evolver.py` | Note evolution with archival |
| Alias Resolver | `memory/alias_resolver.py` | Canonical name resolution |
| Alias Manager | `memory/alias_manager.py` | Auto-update alias tracking |
| Reasoning Logger | `memory/reasoning_logger.py` | Decision audit trail |
| Vector Retriever | `memory/vector_retriever.py` | Semantic search |
| Vector Memory | `memory/vector_memory.py` | Cross-session embeddings |
| Test Suite | `test_memory_system.py` | 33 tests across 8 phases |

---

## 5. Naming Conventions

| Pattern | Example |
|---------|---------|
| Note ID | `note_20260402_182101_6491` (YYYYMMDD_HHMMSS_xxxx) |
| Canonical actor | lowercase, spaces preserved (e.g., `volt typhoon`) |
| Entity type | singular (cve, actor, tool, campaign, sector) |
| Tier assignment | A=authoritative, B=operational, C=support |
| File suffix | `.py` (code), `.jsonl` (data), `.json` (index) |

---

## 6. Common Operations

| Task | Code Location |
|------|---------------|
| Add a note | `mm.remember(content, source_type, domain)` |
| Recall by query | `mm.recall(query, k=10)` |
| Recall by entity | `mm.recall_cve('CVE-2024-3094')`, `mm.recall_actor('volt typhoon')` |
| Get snapshot | `mm.get_snapshot()` |
| Archive notes | `mm.archive_low_confidence_notes()` |
| Get stats | `mm.get_stats()` |
| Rebuild index | `mm.rebuild_entity_index()` |

---

## 7. Known Gotchas

| Issue | Workaround |
|-------|------------|
| Tier A notes cannot be superseded | Use UPDATE_CONTEXT instead of SUPERSEDE |
| LLM enrichment fails | Falls back to basic keyword extraction |
| Entity index stale | Run `mm.rebuild_entity_index()` |
| Alias collision | Resolve manually in alias_maps/*.json |
| Archive path not mounted | Create `/media/rolandpg/USB-HDD/archive/` |
| Reasoning log full | Run `logger.prune_old_entries()` |

---

## 8. Tribal Knowledge

| Knowledge | Source |
|-----------|--------|
| "Rolling 180-day reasoning pruning" | ReasoningLogger default retention |
| "3 observations = auto-add alias" | AliasManager AUTO_THRESHOLD |
| "Max 5 evolution hops" | EvolutionDecider limit |
| "Cold path = /media/rolandpg/USB-HDD" | MemoryManager initialization |
| "Embeddings = nomic-embed-text-v2-moe" | EmbeddingGenerator model |

---

## 9. Cross-References

| Topic | Document Section |
|-------|------------------|
| System Architecture | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Data Flow | [DATAFLOW.md](DATAFLOW.md) |
| Components | [COMPONENTS.md](COMPONENTS.md) |
| API Reference | [API_REFERENCE.md](API_REFERENCE.md) |
| Security | [SECURITY.md](SECURITY.md) |
| Development Setup | [DEVELOPMENT.md](DEVELOPMENT.md) |
| PRD Full Details | [PRD.md](../MEMORY_PRD.md) |

---

## 10. Testing & Maintenance

| Command | Purpose |
|---------|---------|
| `python3 test_memory_system.py` | Run all 57 tests |
| `python3 test_memory_system.py --phase 1` | Phase 1 tests only |
| `python3 test_memory_system.py --verbose` | Verbose output |
| `python3 test_phase_6.py` | Phase 6 tests (36 tests) |
| `python3 test_phase_7.py` | Phase 7 tests (21 tests) |
| `python3 memory_plan_reviewer.py` | Weekly health check |
| `./run_daily.sh` | Daily maintenance |
| `./run_weekly.sh` | Weekly maintenance |

---

*End of LLM Context Document*
