# A-MEM Documentation Index

**Generated:** 2026-04-02  
**Commit:** a3a4953 (git worktree state)  
**Project:** A-MEM (Agentic Memory) - Roland Fleet Agentic Memory System

---

## Documentation Structure

This documentation package is organized for dual consumption: human engineers and LLM-based development tools.

### Suggested Reading Order for Humans

1. **[INDEX.md](INDEX.md)** - This file (overview and quick reference)
2. **[PRD.md](../MEMORY_PRD.md)** - Project requirements and scope
3. **[ARCHITECTURE.md](ARCHITECTURE.md)** - System overview and data flow
4. **[COMPONENTS.md](COMPONENTS.md)** - Component registry and relationships
5. **[DATAFLOW.md](DATAFLOW.md)** - Data lifecycle and transformations
6. **[API_REFERENCE.md](API_REFERENCE.md)** - API and public interface reference
7. **[SECURITY.md](SECURITY.md)** - Security posture and considerations
8. **[DEVELOPMENT.md](DEVELOPMENT.md)** - Local development setup

### Suggested Reading Order for LLM Context Loading

1. **[LLM_CONTEXT.md](LLM_CONTEXT.md)** - Concise context (<8k tokens)
2. **[ARCHITECTURE.md](ARCHITECTURE.md)** - Core architecture
3. **[DATAFLOW.md](DATAFLOW.md)** - Data flows

---

## Quick Answers

| Question | Document Section |
|----------|------------------|
| What does A-MEM do? | PRD Section 1: Problem Statement |
| What are the core features? | PRD Section 5: Technical Architecture |
| How do I add a new feature? | DEVELOPMENT.md |
| What is the memory schema? | note_schema.py MemoryNote class |
| How are entities indexed? | entity_indexer.py EntityIndexer class |
| How are aliases resolved? | alias_resolver.py AliasResolver class |
| Where are notes stored? | notes.jsonl + vector_memory.lance |
| How do I run tests? | test_memory_system.py |
| What is the tier system? | note_constructor.py TIER_RULES |
| What is the evolution system? | memory_evolver.py MemoryEvolver class |

---

## Documentation Files

| File | Description | Size |
|------|-------------|------|
| **[PRD.md](../MEMORY_PRD.md)** | Project Requirement Document - phases 1-7 complete | ~28KB |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | System architecture and data flow narrative | Generated |
| **[DATAFLOW.md](DATAFLOW.md)** | Data lifecycle diagrams and transformations | Generated |
| **[COMPONENTS.md](COMPONENTS.md)** | Component registry with interfaces | Generated |
| **[TECH_STACK.md](TECH_STACK.md)** | Technology stack summary | Generated |
| **[SBOM.md](SBOM.md)** | Software Bill of Materials | Generated |
| **[API_REFERENCE.md](API_REFERENCE.md)** | API reference documentation | Generated |
| **[SECURITY.md](SECURITY.md)** | Security posture and risks | Generated |
| **[DEVELOPMENT.md](DEVELOPMENT.md)** | Development environment setup | Generated |
| **[LLM_CONTEXT.md](LLM_CONTEXT.md)** | Concise context for LLMs (<8k tokens) | Generated |
| **[PARALLEL_EVOLUTION.md](PARALLEL_EVOLUTION.md)** | Performance optimization — parallel evolution (16x speedup) | v1.0 |
| **[PRD_PRODUCTPLAN_COMPARISON.md](PRD_PRODUCTPLAN_COMPARISON.md)** | Alignment analysis between PRD and Product Plan | v1.0 |

---

## Project Status

| Phase | Status | Tests |
|-------|--------|-------|
| Phase 1: Entity Indexing | ✅ Complete | 14/14 passing |
| Phase 2: Entity-Guided Linking | ✅ Complete | 5/5 passing |
| Phase 3: Date-Aware Retrieval | ✅ Complete | 3/3 passing |
| Phase 4: Mid-Session Snapshot | ✅ Complete | 2/2 passing |
| Phase 5: Cold Archive | ✅ Complete | 3/3 passing |
| Phase 2.5: Alias Resolution | ✅ Complete | 10/10 passing (131.6s) |
| Phase 3.5: Alias Auto-Update | ✅ Complete | 7/7 passing (84.3s) |
| Phase 4.5: Epistemic Tiering | ✅ Complete | 10/10 passing (29.9s) |
| Phase 5.5: Reasoning Memory | ✅ Complete | 9/9 passing |
| Phase 6: Ontology & Knowledge Graph | ✅ Complete | 36/36 tests passing (124.3s) |
| Phase 7: Synthesis Layer (RAG-as-Answer) | ✅ Complete | 21/21 tests passing (89.7s) |
| Integration (6↔7) | ✅ Complete | 11/11 tests passing (20.9s) |
| Performance Tests | ✅ Complete | 6/6 tests passing (2.7s) |

---

## Performance Metrics

| Test | Target | Actual |
|------|--------|--------|
| Note creation rate | > 100 notes/sec | **1151.7 notes/sec** |
| Edge creation rate | > 1000 edges/sec | **4517.8 edges/sec** |
| Graph traversal latency | < 50ms | **0.00ms** |
| Context retrieval latency | < 500ms | **137.42ms** |
| Memory for 500 notes | < 100MB | **0.1MB** |

**Test Command:** `python3 test_performance.py`

**Grand Total:** 136/136 tests passing

---

## Directory Structure

```
memory/
├── docs/                      # This documentation package
│   ├── INDEX.md              # This file
│   ├── PRD.md                # Project Requirement Document
│   ├── ARCHITECTURE.md       # Architecture overview
│   ├── DATAFLOW.md           # Data flow documentation
│   ├── COMPONENTS.md         # Component registry
│   ├── TECH_STACK.md         # Technology stack
│   ├── SBOM.md               # Software Bill of Materials
│   ├── API_REFERENCE.md      # API reference
│   ├── SECURITY.md           # Security posture
│   ├── DEVELOPMENT.md        # Development guide
│   └── LLM_CONTEXT.md        # LLM context document
├── memory/                    # Subdirectory for core files
│   ├── alias_maps/           # Entity alias mappings
│   │   └── actors.json       # Actor alias map with 18+ canonical entities
│   └── briefings/            # Security briefings
├── notes/                     # Topic notes (PARA structure)
├── cti-briefings/            # CTI briefings
├── vector_memory.lance/      # LanceDB vector store
├── __pycache__/              # Python cache
├── notes.jsonl               # Main note storage (167 notes)
├── entity_index.json         # Entity → note ID index
├── reasoning_log.jsonl       # Evolution/link decision log
├── dedup_log.jsonl           # Deduplication log
├── plan_iterations.jsonl     # PRD iteration history
├── alias_observations.json   # Phase 3.5 auto-update tracking
├── test_memory_system.py     # Main test suite
├── test_phase_3_5.py         # Alias resolution tests
├── test_phase_4_5.py         # Epistemic tiering tests
├── test_phase_5_5.py         # Reasoning memory tests (9 tests)
├── test_integration.py       # Phase 6/7 integration tests (11 tests)
└── test_performance.py       # Performance & scaling tests (6 tests)
```

---

## Key Concepts

### Zettelkasten-inspired Architecture
A-MEM implements a digital zettelkasten ( Slipbox) system where notes are atomic, linked, and can evolve over time. Key features:
- **Atomic notes** - Single idea per note
- **Bidirectional links** - Notes connect to related concepts
- **Evolution** - Notes can be updated and superseded by newer information
- **Entity indexing** - Fast lookup by CVE, actor, tool, campaign, sector

### Epistemic Tiering (Phase 4.5)
Notes are assigned one of three tiers based on source:
- **Tier A (Authoritative)**: Human/Tool/observation sources - cannot be superseded by lower tiers
- **Tier B (Operational)**: Agent reports - can supersede C but not A
- **Tier C (Support)**: Summaries/hypotheses - never triggers supersession

### Alias Resolution (Phase 3.5)
Threat actors are tracked with canonical names and aliases:
- MuddyWater, Mercury, TEMP.Zagros → `muddywater` (canonical)
- Volt Typhoon, Vult Typhoon → `volt typhoon` (canonical)
- Auto-add aliases after 3 observations

---

## Maintenance

### Running Tests
```bash
python3 memory/test_memory_system.py          # All core tests (33 tests)
python3 memory/test_memory_system.py --phase 1  # Phase 1 only
python3 memory/test_memory_system.py --verbose  # Verbose output
python3 memory/test_phase_6.py                  # Phase 6 tests (36 tests)
python3 memory/test_phase_7.py                  # Phase 7 tests (21 tests)
python3 memory/test_integration.py              # Phase 6/7 integration tests (11 tests)
python3 memory/test_performance.py              # Performance & scaling tests (6 tests)
```

### Running Plan Review
```bash
python3 memory/memory_plan_reviewer.py        # Weekly health check
```

### Daily Maintenance
```bash
./run_daily.sh           # Daily maintenance tasks
./run_weekly.sh          # Weekly maintenance tasks
```

---

## Support

For questions about this documentation or the codebase, see:
- `AGENTS.md` - Agent agent guidance
- `SOUL.md` - System identity and purpose
- `RUNBOOK.md` - Operational procedures

---

*This documentation was generated by the Software Documenter agent.*
*Last updated: 2026-04-02T18:30:00Z*
