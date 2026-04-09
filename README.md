# ZettelForge: Agentic Memory System

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-1.5.0-green.svg)](https://github.com/rolandpg/zettelforge)

A production-grade memory system for AI agents, purpose-built for cyber threat intelligence (CTI). Combines vector semantic search, knowledge graph traversal, and intent-based query routing to give agents persistent, structured memory across sessions.

## Features

- **Blended Retrieval**: Combines vector similarity + knowledge graph traversal, weighted by query intent
- **Knowledge Graph**: Entity nodes, relationship edges, temporal indexing, multi-hop traversal (BFS, max-depth configurable)
- **Two-Phase Extraction Pipeline**: Mem0-style selective ingestion — LLM extracts salient facts with importance scores, then decides ADD/UPDATE/DELETE/NOOP per fact to keep memory coherent
- **Entity Extraction**: Automatic indexing of CVEs, threat actors, tools, campaigns with alias resolution
- **Intent-Based Routing**: Classifies queries as factual/temporal/relational/causal/exploratory and adjusts retrieval weights accordingly
- **RAG Synthesis**: Answer generation from retrieved memories in multiple formats (direct answer, brief, timeline, relationship map)
- **Causal Triple Extraction**: LLM-based subject-relation-object extraction stored as graph edges
- **CTI Integration**: Connectors for OpenCTI platform, Sigma rule generation from IOCs
- **Local-First**: Runs entirely on local hardware — Ollama for LLM, LanceDB for vectors, JSONL for persistence

## Quick Start

```bash
# Install from source
git clone https://github.com/rolandpg/zettelforge.git
cd zettelforge
pip install -e ".[dev]"

# Ollama setup (required for embeddings and LLM)
ollama pull nomic-embed-text
ollama pull qwen2.5:3b
```

```python
from zettelforge import MemoryManager

mm = MemoryManager()

# Store a memory (append-only, fast)
note, status = mm.remember(
    "APT28 uses Cobalt Strike for lateral movement via CVE-2024-1111",
    domain="cti"
)

# Store with two-phase extraction (selective, deduplicating)
results = mm.remember_with_extraction(
    "APT28 has shifted tactics. They dropped DROPBEAR and now exploit edge devices.",
    domain="cti"
)
# results: [(<MemoryNote>, "added"), (<MemoryNote>, "updated"), ...]

# Retrieve — blends vector similarity + graph traversal
results = mm.recall("What tools does APT28 use?", k=10)

# Fast entity lookup
apt28_notes = mm.recall_actor("APT28")
cve_notes = mm.recall_cve("CVE-2024-1111")

# Synthesize answers from memories
result = mm.synthesize(
    "What do we know about APT28?",
    format="synthesized_brief"
)

# Traverse the knowledge graph
paths = mm.traverse_graph("actor", "apt28", max_depth=2)
# APT28 -[USES_TOOL]-> cobalt-strike -[EXPLOITS_CVE]-> CVE-2024-1111
```

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                          MemoryManager                           │
│  remember()  remember_with_extraction()  recall()  synthesize()  │
├──────────┬───────────┬──────────────┬───────────┬────────────────┤
│  Note    │  Fact     │   Memory     │  Blended  │   Synthesis    │
│Constructor│ Extractor │  Updater     │ Retriever │   Generator    │
│(enrich)  │(Phase 1)  │(Phase 2)     │(vec+graph)│   (RAG)        │
├──────────┴───────────┴──────────────┼───────────┴────────────────┤
│       Entity Indexer + Alias        │  Intent Classifier         │
│       Resolver + Governance         │  (factual/temporal/causal) │
├─────────────────────────────────────┼────────────────────────────┤
│          MemoryStore (JSONL)        │   Knowledge Graph (JSONL)  │
│          LanceDB (vectors)          │   Temporal Index           │
└─────────────────────────────────────┴────────────────────────────┘
```

### Retrieval Pipeline

```
Query → Intent Classifier → Traversal Policy (weights)
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
              VectorRetriever  GraphRetriever  EntityIndex
              (cosine sim +    (BFS from query  (O(1) lookup)
               entity boost)   entities, hop
                               distance scoring)
                    │               │               │
                    └───────┬───────┘               │
                            ▼                       │
                     BlendedRetriever ◄─────────────┘
                     (policy-weighted merge,
                      dedup, rank)
                            │
                            ▼
                      List[MemoryNote]
```

## Benchmarks

Evaluated across three benchmark suites (2026-04-09):

| Benchmark | What it measures | Key result |
|-----------|-----------------|------------|
| [LOCOMO](https://snap-research.github.io/locomo/) (ACL 2024) | Conversational memory recall | 15.0% accuracy, 0.33 avg score |
| [CTIBench](https://huggingface.co/datasets/AI4Sec/cti-bench) (NeurIPS 2024) | CTI entity extraction & attribution | Baseline established |
| RAGAS | Retrieval quality | 75.9% keyword presence |

### LOCOMO Results (v1.3.0 → v1.5.0)

| Category | v1.3.0 | v1.5.0 | Change |
|----------|--------|--------|--------|
| single-hop | 5.0% | 10.0% | +5.0 |
| multi-hop | 0.0% | 0.0% | avg_score 0.0 → 0.15 |
| temporal | 0.0% | 0.0% | — |
| open-domain | 30.0% | 30.0% | avg_score +0.025 |
| adversarial | 35.0% | 35.0% | — |
| **Overall** | **14.0%** | **15.0%** | **+1pp, p95 latency 190s → 1.3s** |

LOCOMO tests conversational memory (people, hobbies) — ZettelForge's entity extractor targets CTI entities, so graph traversal doesn't fire on conversational queries. See the [full benchmark report](benchmarks/BENCHMARK_REPORT.md) for analysis and roadmap.

### Comparison to SOTA

| System | LOCOMO Accuracy | p95 Latency |
|--------|----------------|-------------|
| Mem0g | 68.5% | 2.6s |
| Mem0 | 66.9% | 1.4s |
| OpenAI Memory | 52.9% | 0.9s |
| **ZettelForge 1.5.0** | **15.0%** | **1.3s** |

## Installation

### Requirements

- Python 3.10+
- [Ollama](https://ollama.com) (local LLM + embeddings)

### From Source

```bash
git clone https://github.com/rolandpg/zettelforge.git
cd zettelforge
pip install -e ".[dev]"
```

### Ollama Setup

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull nomic-embed-text    # embeddings (768-dim)
ollama pull qwen2.5:3b          # LLM for extraction, classification, synthesis
ollama serve
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `AMEM_DATA_DIR` | `~/.amem` | Data storage directory |
| `AMEM_EMBEDDING_URL` | `http://127.0.0.1:8081` | Embedding server endpoint |
| `AMEM_EMBEDDING_MODEL` | `nomic-embed-text-v2-moe.gguf` | Embedding model |

## API Reference

### MemoryManager

Primary interface for all memory operations.

#### `remember(content, source_type, source_ref, domain)`

Append-only storage. Constructs enriched note, extracts entities, updates knowledge graph.

```python
note, status = mm.remember("APT28 targets NATO", domain="cti")
# status: "created"
```

#### `remember_with_extraction(content, domain, context, min_importance, max_facts)`

Two-phase Mem0-style pipeline. Phase 1: LLM extracts salient facts with importance scores. Phase 2: Each fact compared to existing notes — ADD/UPDATE/DELETE/NOOP.

```python
results = mm.remember_with_extraction(
    "APT28 dropped DROPBEAR, now uses edge device exploitation",
    domain="cti", min_importance=3
)
# returns: [(MemoryNote, "added"), (MemoryNote, "updated"), ...]
```

#### `recall(query, domain, k, include_links, exclude_superseded)`

Blended retrieval combining vector similarity and knowledge graph traversal, weighted by query intent.

```python
results = mm.recall("What tools does APT28 use?", k=10)
```

#### `synthesize(query, format, k, tier_filter)`

RAG synthesis over retrieved memories.

```python
result = mm.synthesize("Summarize APT28 activity", format="synthesized_brief")
# formats: "direct_answer", "synthesized_brief", "timeline_analysis", "relationship_map"
```

#### Entity Lookups

```python
mm.recall_cve("CVE-2024-3094")     # Fast CVE lookup
mm.recall_actor("APT28")           # Threat actor lookup
mm.recall_tool("cobalt-strike")    # Tool/malware lookup
```

#### Knowledge Graph

```python
mm.traverse_graph("actor", "apt28", max_depth=2)
mm.get_entity_relationships("actor", "apt28")
```

## Project Structure

```
src/zettelforge/
    memory_manager.py       # Primary agent interface
    note_schema.py          # Pydantic MemoryNote model
    note_constructor.py     # Content enrichment, entity extraction
    memory_store.py         # JSONL + LanceDB persistence
    fact_extractor.py       # Phase 1: LLM salient fact extraction
    memory_updater.py       # Phase 2: ADD/UPDATE/DELETE/NOOP decisions
    knowledge_graph.py      # Graph storage with temporal indexing
    graph_retriever.py      # BFS traversal, hop-distance scoring
    blended_retriever.py    # Merge vector + graph with policy weights
    vector_retriever.py     # Cosine similarity + entity boost
    intent_classifier.py    # Query intent routing
    entity_indexer.py       # Entity extraction and O(1) index
    alias_resolver.py       # Entity alias canonicalization
    synthesis_generator.py  # RAG answer generation
    cti_integration.py      # OpenCTI platform connector
    sigma_generator.py      # Sigma rule generation from IOCs
    context_injection.py    # Proactive agent context loading

benchmarks/
    BENCHMARK_REPORT.md     # Unified results and analysis
    locomo_benchmark.py     # LOCOMO evaluation script
    ctibench_benchmark.py   # CTIBench adapter (NeurIPS 2024)
    ragas_benchmark.py      # RAGAS retrieval quality wrapper

tests/
    test_basic.py           # Unit tests
    test_e2e.py             # End-to-end integration
    test_fact_extractor.py  # Two-phase extraction tests
    test_memory_updater.py  # UPDATE/DELETE operation tests
    test_graph_retriever.py # Graph traversal tests
    test_blended_retriever.py # Blended scoring tests
    test_recall_integration.py # Full recall pipeline tests
    test_two_phase_e2e.py   # Extraction pipeline e2e
```

## Development

```bash
git clone https://github.com/rolandpg/zettelforge.git
cd zettelforge
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run benchmarks
python benchmarks/locomo_benchmark.py --samples 20
python benchmarks/ctibench_benchmark.py --task ate --samples 50
python benchmarks/ragas_benchmark.py --samples 20

# Format and lint
black src/zettelforge/
ruff check src/zettelforge/
```

## Roadmap

- [x] Core storage and retrieval (JSONL + LanceDB)
- [x] Entity extraction and indexing (CVEs, actors, tools, campaigns)
- [x] Knowledge graph with temporal indexing
- [x] Intent-based query routing
- [x] RAG synthesis layer
- [x] Causal triple extraction
- [x] CTI platform integration + Sigma generation
- [x] Mem0-style two-phase extraction pipeline (v1.4.0)
- [x] Graph traversal retrieval with blended scoring (v1.5.0)
- [x] Benchmark suite: LOCOMO + CTIBench + RAGAS
- [ ] Conversational entity extractor (improve LOCOMO from 15% to ~30%)
- [ ] CTIBench adapter fixes (ATT&CK DB cross-reference, per-report queries)
- [ ] LLM-judge scoring for benchmarks

## License

MIT License - see [LICENSE](LICENSE) file

## Acknowledgments

- Inspired by [Zettelkasten](https://en.wikipedia.org/wiki/Zettelkasten) and [A-Mem](https://arxiv.org/abs/2602.10715) (NeurIPS 2025)
- Two-phase pipeline inspired by [Mem0](https://mem0.ai/research) architecture
- Benchmarked against [LOCOMO](https://snap-research.github.io/locomo/) (ACL 2024) and [CTIBench](https://arxiv.org/abs/2406.07599) (NeurIPS 2024)
- Embeddings: [Ollama](https://ollama.com) | Vectors: [LanceDB](https://lancedb.com) | Schema: [Pydantic](https://pydantic.dev)

## Links

- Repository: https://github.com/rolandpg/zettelforge
- Issues: https://github.com/rolandpg/zettelforge/issues
- Benchmark Report: [benchmarks/BENCHMARK_REPORT.md](benchmarks/BENCHMARK_REPORT.md)
