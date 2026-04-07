---
name: zettelforge
description: ZettelForge (Agentic Memory System) - A production-grade agent memory system with vector search, knowledge graph, entity indexing, and synthesis layer. Use this skill when the user wants to store, retrieve, or synthesize information across sessions, build persistent agent memory, or implement RAG-as-answer capabilities. Automatically triggers on memory-related requests, persistence needs, cross-session recall, or knowledge management tasks.
---

# ZettelForge: Agentic Memory System

A production-grade memory system for AI agents. Store, retrieve, and synthesize information with vector search, knowledge graphs, and entity-aware linking.

## Quick Start

```python
from zettelforge import MemoryManager

# Initialize
mm = MemoryManager()

# Store a memory
note, reason = mm.remember("CVE-2024-3094 is a backdoor in XZ Utils")

# Retrieve memories
results = mm.recall("XZ backdoor", k=5)

# Entity lookup
apt28_notes = mm.recall_actor("APT28", k=10)
cve_notes = mm.recall_cve("CVE-2024-3094")

# Synthesize answer
answer = mm.synthesize("What do we know about XZ backdoor?", format="direct_answer")
```

## Installation

```bash
pip install amem
```

Or install from source:
```bash
git clone https://github.com/rolandpg/amem.git
cd amem
pip install -e .
```

## Core Features

| Feature | Description |
|---------|-------------|
| **Vector Storage** | LanceDB-backed semantic search with Ollama embeddings |
| **Entity Indexing** | Automatic extraction of CVEs, actors, tools, campaigns |
| **Knowledge Graph** | Relationship mapping between entities and notes |
| **Synthesis Layer** | RAG-as-answer with multiple output formats |
| **Alias Resolution** | Normalized entity names (e.g., "Fancy Bear" → "apt28") |
| **Epistemic Tiers** | A/B/C quality classification |
| **Cold Archive** | Automatic archival of low-confidence notes |

## Architecture

```
User Query → MemoryManager
    ├── Vector Retriever (semantic search)
    ├── Entity Index (fast lookup)
    ├── Knowledge Graph (relationships)
    └── Synthesis Layer (RAG-as-answer)
```

## Response Formats

- `direct_answer`: Concise answer with sources
- `synthesized_brief`: Thematic analysis
- `timeline_analysis`: Chronological events
- `relationship_map`: Entity connections

## Configuration

Environment variables:
```bash
AMEM_DATA_DIR=/path/to/data    # Default: ~/.amem
AMEM_OLLAMA_URL=http://localhost:11434
AMEM_EMBEDDING_MODEL=nomic-embed-text
```

## API Reference

See `docs/API.md` for complete API documentation.

## Development

```bash
# Run tests
python -m pytest tests/ -v

# Run specific phase tests
python tests/test_phase_7.py
```

## License

MIT License - See LICENSE file
