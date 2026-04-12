# ZettelForge: Agentic Memory System

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/rolandpg/zettelforge/actions/workflows/ci.yml/badge.svg)](https://github.com/rolandpg/zettelforge/actions)
[![Version](https://img.shields.io/badge/version-2.1.0-green.svg)](https://github.com/rolandpg/zettelforge/releases)

A production-grade memory system for AI agents, purpose-built for cyber threat intelligence (CTI). Combines **LanceDB vector search** with a **knowledge graph**, blended retrieval, and intent-based query routing to give agents persistent, structured memory across sessions.

Built by [Threatengram](https://threatengram.com).

## Quick Start

```bash
pip install -e .
```

```python
from zettelforge import MemoryManager

mm = MemoryManager()

# Store a memory
note, status = mm.remember(
    "APT28 uses Cobalt Strike for lateral movement via CVE-2024-1111",
    domain="cti"
)

# Two-phase extraction — LLM extracts facts, decides ADD/UPDATE/DELETE
results = mm.remember_with_extraction(
    "APT28 has shifted tactics. They dropped DROPBEAR and now exploit edge devices.",
    domain="cti"
)

# Retrieve — blends vector similarity + knowledge graph traversal
results = mm.recall("What tools does APT28 use?", k=10)

# Alias resolution works automatically
results = mm.recall_actor("Fancy Bear")  # resolves to APT28

# Synthesize answers from memory
result = mm.synthesize("Summarize APT28 activity")
```

No external services required. Embeddings run in-process via fastembed (ONNX), knowledge graph uses JSONL, LLM uses llama-cpp-python. Everything runs on your laptop.

## Features

- **Two-Phase Extraction Pipeline**: Mem0-style selective ingestion -- LLM extracts salient facts with importance scores, then decides ADD/UPDATE/DELETE/NOOP per fact
- **Blended Retrieval**: Combines vector similarity + knowledge graph traversal, weighted by query intent (factual, temporal, relational, causal, exploratory)
- **Cross-Encoder Reranking**: ms-marco-MiniLM reranks results by query-document relevance
- **Entity Extraction**: Automatic indexing of CVEs, threat actors, tools, campaigns, people, locations, organizations, events (10 types, regex + LLM NER)
- **Causal Triple Extraction**: LLM infers relationships ("APT28 uses DROPBEAR") and stores them as graph edges
- **Knowledge Graph**: Entity nodes, relationship edges, JSONL persistence with append-only writes
- **RAG Synthesis**: Answer generation from retrieved memories
- **Intent Classification**: Adaptive query routing with per-intent retrieval weights
- **Zero-Server Embeddings**: 768-dim vectors generated in-process via fastembed (ONNX, 7ms/embed)
- **Local-First**: Runs entirely on local hardware -- no cloud dependencies, no API keys needed
- **MCP Server**: Expose memory as tools for Claude Code, OpenClaw, or any MCP-compatible agent

## Community vs Enterprise

**ZettelForge Community** (MIT) includes everything above. It is a complete, production-ready memory system.

**[ThreatRecall Enterprise](https://threatengram.com/enterprise)** (BSL-1.1) adds scale, analyst workflows, and platform integrations for teams running ZettelForge in production:

| Enterprise Feature | What it adds |
|---|---|
| TypeDB STIX 2.1 ontology | Replaces JSONL graph with TypeDB -- inference rules, 9 entity types, 8 relation types, 36 seeded CTI aliases |
| Temporal KG queries | "What changed since Tuesday?" -- `get_changes_since()`, `get_entity_timeline()` |
| Multi-hop graph traversal | `traverse_graph()` with BFS across relationship chains |
| Advanced synthesis formats | `synthesized_brief`, `timeline_analysis`, `relationship_map` |
| Report ingestion | `remember_report()` with auto-chunking for long threat reports |
| OpenCTI integration | Bi-directional sync with OpenCTI platform |
| Sigma rule generation | Generate Sigma YAML detection rules from IOCs |
| Multi-tenant auth | OAuth/JWT with per-tenant data isolation |
| Proactive context injection | Auto-load relevant context before agent tasks |

```bash
# Enterprise install (requires license key)
pip install -e ".[enterprise]"
export THREATENGRAM_LICENSE_KEY="TG-xxxx-xxxx-xxxx-xxxx"
```

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                           MemoryManager                              │
│  remember()  remember_with_extraction()  recall()  synthesize()      │
├──────────┬───────────┬──────────────┬───────────┬────────────────────┤
│  Note    │  Fact     │   Memory     │  Blended  │   Synthesis        │
│Constructor│ Extractor │  Updater     │ Retriever │   Generator        │
│(enrich)  │(Phase 1)  │(Phase 2)     │(vec+graph)│   (RAG)            │
├──────────┴───────────┴──────────────┼───────────┴────────────────────┤
│       Entity Indexer + Alias        │  Intent Classifier             │
│       Resolver                      │  (factual/temporal/causal)     │
├─────────────────────────────────────┼────────────────────────────────┤
│   Knowledge Graph (JSONL)           │  LanceDB (Vectors)             │
│   Entity nodes + relationship edges │  768-dim fastembed embeddings  │
│   Temporal indexing                 │  Zettelkasten notes            │
│   [Enterprise: TypeDB STIX 2.1]    │  IVF_PQ index                  │
└─────────────────────────────────────┴────────────────────────────────┘
```

## API Reference

### Store

```python
# Direct storage
note, status = mm.remember("APT28 targets NATO", domain="cti")

# Two-phase extraction (LLM-powered)
results = mm.remember_with_extraction(content, domain="cti", min_importance=3)

# Report ingestion [Enterprise]
results = mm.remember_report(content, source_url="...", published_date="2026-04-09")
```

### Retrieve

```python
# Blended recall (vector + graph, intent-weighted)
results = mm.recall("What tools does APT28 use?", k=10)

# Entity lookups
mm.recall_cve("CVE-2024-3094")
mm.recall_actor("Fancy Bear")       # alias -> APT28
mm.recall_tool("cobalt-strike")

# Knowledge graph
mm.get_entity_relationships("actor", "apt28")
mm.traverse_graph("actor", "apt28", max_depth=2)  # [Enterprise]
```

### Synthesize

```python
result = mm.synthesize("Summarize APT28 activity")
# Enterprise formats: "synthesized_brief", "timeline_analysis", "relationship_map"
```

### Edition Detection

```python
from zettelforge import is_enterprise, edition_name

print(edition_name())  # "ZettelForge Community" or "ThreatRecall Enterprise by Threatengram"
```

## Deployment

### Local Development (recommended to start)

```bash
git clone https://github.com/rolandpg/zettelforge.git
cd zettelforge
pip install -e ".[dev]"

# Run tests (no external services needed)
ZETTELFORGE_BACKEND=jsonl pytest tests/ -v --ignore=tests/test_typedb_client.py

# Quick smoke test
python3 -c "
from zettelforge import MemoryManager
mm = MemoryManager()
note, _ = mm.remember('APT28 uses Cobalt Strike', domain='cti')
print(f'Stored: {note.id}')
results = mm.recall('APT28 tools', k=3)
print(f'Recalled: {len(results)} results')
"
```

### With Ollama (better LLM quality)

```bash
# Install Ollama and pull a model
ollama pull qwen2.5:3b
ollama serve

# ZettelForge auto-detects Ollama for extraction/synthesis
```

### With TypeDB [Enterprise]

```bash
# Start TypeDB
docker compose -f docker/docker-compose.yml up -d

# Set backend
export ZETTELFORGE_BACKEND=typedb

# Seed CTI aliases (one-time)
python3 -c "from zettelforge.schema.seed_aliases import seed_aliases; seed_aliases()"
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `AMEM_DATA_DIR` | `~/.amem` | Data directory (LanceDB vectors + JSONL notes) |
| `ZETTELFORGE_BACKEND` | `typedb` | `typedb` [Enterprise] or `jsonl` |
| `ZETTELFORGE_EMBEDDING_PROVIDER` | `fastembed` | `fastembed` (in-process) or `ollama` |
| `ZETTELFORGE_LLM_PROVIDER` | `local` | `local` (llama-cpp) or `ollama` |
| `THREATENGRAM_LICENSE_KEY` | | Enterprise license key (`TG-xxxx-xxxx-xxxx-xxxx`) |

See [config.default.yaml](config.default.yaml) for all options.

## Benchmarks

| Benchmark | What it measures | Score |
|-----------|-----------------|-------|
| [CTI Retrieval](benchmarks/BENCHMARK_REPORT.md) | Attribution, CVE linkage, multi-hop | 75.0% |
| [LOCOMO](https://snap-research.github.io/locomo/) (ACL 2024) | Conversational memory recall | 18.0% |
| [RAGAS](benchmarks/BENCHMARK_REPORT.md) | Retrieval quality (keyword presence) | 78.1% |

See the [full benchmark report](benchmarks/BENCHMARK_REPORT.md) for methodology and analysis.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, and the Community/Enterprise boundary.

## License

- **Community**: [MIT License](LICENSE)
- **Enterprise**: [BSL-1.1](LICENSE-ENTERPRISE) (converts to Apache-2.0 after 4 years)

## Acknowledgments

- Inspired by [Zettelkasten](https://en.wikipedia.org/wiki/Zettelkasten) and [A-Mem](https://arxiv.org/abs/2602.10715) (NeurIPS 2025)
- Two-phase pipeline inspired by [Mem0](https://mem0.ai/research) architecture
- STIX 2.1 schema informed by [typedb-cti](https://github.com/typedb-osi/typedb-cti)
- Benchmarked against [LOCOMO](https://snap-research.github.io/locomo/) (ACL 2024) and [CTIBench](https://arxiv.org/abs/2406.07599) (NeurIPS 2024)
- [TypeDB](https://typedb.com) | [LanceDB](https://lancedb.com) | [fastembed](https://github.com/qdrant/fastembed) | [Pydantic](https://pydantic.dev)
