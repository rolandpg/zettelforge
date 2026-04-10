# ZettelForge Skill Package - Summary

## What Was Created

A standalone, production-ready Python package for ZettelForge (internal codebase name) / ThreatRecall (product name) — an agentic memory system for cyber threat intelligence that can be:
1. Installed as a Python package via pip
2. Used as an OpenClaw skill
3. Published to GitHub as an open-source project
4. Eventually published to PyPI

## Directory Structure

```
zettelforge/
├── .github/workflows/ci.yml    # GitHub Actions CI/CD
├── .gitignore                   # Git ignore rules
├── CONTRIBUTING.md              # Contribution guidelines
├── LICENSE                      # MIT License
├── MANIFEST.in                  # Package manifest
├── README.md                    # Project documentation
├── SKILL.md                     # OpenClaw skill definition
├── pyproject.toml               # Python package config
├── config.default.yaml          # Default configuration
├── config.example.yaml          # Example configuration
├── docker/
│   └── docker-compose.yml       # TypeDB container
├── src/zettelforge/             # Source code
│   ├── __init__.py              # Package init
│   ├── memory_manager.py        # Primary agent interface
│   ├── typedb_client.py         # TypeDB STIX 2.1 knowledge graph client
│   ├── note_schema.py           # Pydantic MemoryNote model
│   ├── note_constructor.py      # Content enrichment, entity extraction
│   ├── memory_store.py          # JSONL + LanceDB persistence
│   ├── fact_extractor.py        # Phase 1: LLM salient fact extraction
│   ├── memory_updater.py        # Phase 2: ADD/UPDATE/DELETE/NOOP decisions
│   ├── knowledge_graph.py       # Graph factory (TypeDB-first, JSONL fallback)
│   ├── graph_retriever.py       # BFS traversal, hop-distance scoring
│   ├── blended_retriever.py     # Merge vector + graph with policy weights
│   ├── vector_retriever.py      # Cosine similarity + entity boost
│   ├── vector_memory.py         # LanceDB vector store implementation
│   ├── intent_classifier.py     # Query intent routing
│   ├── entity_indexer.py        # Entity extraction and O(1) index
│   ├── alias_resolver.py        # TypeDB alias resolution + JSON fallback
│   ├── synthesis_generator.py   # RAG answer generation
│   ├── synthesis_validator.py   # Synthesis output validation
│   ├── governance_validator.py  # Governance controls (GOV-003/007/011/012)
│   ├── context_injection.py     # Proactive agent context loading
│   ├── cti_integration.py       # OpenCTI platform connector
│   ├── sigma_generator.py       # Sigma rule generation from IOCs
│   ├── llm_client.py            # LLM provider abstraction (local/Ollama)
│   ├── config.py                # Configuration loading and validation
│   ├── cache.py                 # Result caching layer
│   ├── observability.py         # Logging, metrics, and tracing
│   ├── ontology.py              # TypeDB ontology helpers
│   ├── retry.py                 # Retry/backoff utilities
│   └── schema/
│       ├── stix_core.tql        # STIX 2.1 TypeQL schema definition
│       ├── stix_rules.tql       # TypeDB inference functions
│       └── seed_aliases.py      # CTI alias seeding script
├── benchmarks/
│   ├── BENCHMARK_REPORT.md      # Unified results and analysis
│   ├── locomo_benchmark.py      # LOCOMO evaluation script
│   ├── ctibench_benchmark.py    # CTIBench adapter (NeurIPS 2024)
│   └── ragas_benchmark.py       # RAGAS retrieval quality wrapper
└── tests/
    └── (test suite — 82 tests)
```

## Key Features Packaged

| Feature | Status | File |
|---------|--------|------|
| Core MemoryNote schema | ✅ | note_schema.py |
| JSONL + LanceDB storage | ✅ | memory_store.py |
| Vector storage (LanceDB, 768-dim IVF_PQ) | ✅ | vector_memory.py |
| Semantic retrieval | ✅ | vector_retriever.py |
| Entity extraction (10 types) | ✅ | entity_indexer.py |
| Entity-based fast lookup | ✅ | memory_manager.py |
| Main API (remember/recall/synthesize) | ✅ | memory_manager.py |
| TypeDB STIX 2.1 knowledge graph | ✅ | typedb_client.py |
| 36 seeded CTI aliases | ✅ | schema/seed_aliases.py |
| Two-phase extraction pipeline | ✅ | fact_extractor.py, memory_updater.py |
| Blended vector + graph retrieval | ✅ | blended_retriever.py |
| Intent-based query routing | ✅ | intent_classifier.py |
| RAG synthesis (4 formats) | ✅ | synthesis_generator.py |
| Report ingestion (chunked) | ✅ | memory_manager.py |
| In-process embeddings (fastembed) | ✅ | vector_memory.py |
| In-process LLM (llama-cpp-python) | ✅ | llm_client.py |
| Cross-encoder reranking | ✅ | vector_retriever.py |
| Governance enforcement | ✅ | governance_validator.py |
| Proactive context injection | ✅ | context_injection.py |
| Sigma rule generation | ✅ | sigma_generator.py |
| OpenCTI platform connector | ✅ | cti_integration.py |
| Causal triple extraction | ✅ | knowledge_graph.py |
| Alias resolution | ✅ | alias_resolver.py |
| TypeDB-first with JSONL fallback | ✅ | knowledge_graph.py |

## Installation

### Local Development

```bash
git clone https://github.com/rolandpg/zettelforge.git
cd zettelforge
pip install -e ".[dev]"
```

### Usage

```python
from zettelforge import MemoryManager

mm = MemoryManager()

# Store memory
note, status = mm.remember("APT28 uses Cobalt Strike", domain="cti")

# Retrieve
results = mm.recall("APT28 tools", k=5)

# Entity lookup
cve_notes = mm.recall_cve("CVE-2024-3094")

# Synthesize
result = mm.synthesize("Summarize APT28 activity", format="synthesized_brief")
```

## Publishing to GitHub

The package is already published at: https://github.com/rolandpg/zettelforge

To publish updates:
```bash
git add .
git commit -m "feat: your change"
git push origin master
```

## Future: Publish to PyPI

```bash
# Build package
python -m build

# Upload to PyPI (requires account)
python -m twine upload dist/*
```

## Configuration

Environment variables for customization:

```bash
export AMEM_DATA_DIR=/path/to/data          # Default: ~/.amem
export ZETTELFORGE_BACKEND=typedb           # "typedb" or "jsonl" (fallback)
export ZETTELFORGE_EMBEDDING_PROVIDER=fastembed  # "fastembed" (default) or "ollama"
export TYPEDB_HOST=localhost
export TYPEDB_PORT=1729
export TYPEDB_DATABASE=zettelforge
```

## Version

Current: **2.0.0**

Following semantic versioning:
- 2.0.0: Production ready — hybrid TypeDB + LanceDB, STIX 2.1, fastembed, two-phase pipeline

## Git Commit

Latest release: `v2.0.0`

```
ZettelForge v2.0.0: Hybrid TypeDB + LanceDB agentic memory system
```

## Ready for Production

The package is ready for:
- ✅ Local installation and testing
- ✅ GitHub repository
- ✅ CI/CD pipeline (GitHub Actions)
- ✅ OpenClaw skill usage
- ✅ TypeDB STIX 2.1 ontology layer
- ✅ In-process AI (fastembed + llama-cpp-python, no external servers)
- 🔄 Future PyPI publication

---

Created: 2026-04-05
Updated: 2026-04-10
