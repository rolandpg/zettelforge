# A-MEM: Agentic Memory System

[![PyPI version](https://badge.fury.io/py/amem.svg)](https://badge.fury.io/py/amem)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A production-grade memory system for AI agents with vector search, knowledge graph relationships, entity extraction, and RAG-as-answer synthesis.

## Features

- **Vector Semantic Search**: LanceDB-backed storage with Ollama embeddings
- **Entity Extraction**: Automatic indexing of CVEs, threat actors, tools, campaigns
- **Fast Entity Lookup**: O(1) retrieval by entity type and value
- **Link Expansion**: Follow related notes for comprehensive context
- **RAG-as-Answer (Phase 7)**: Synthesize answers from memories with multiple output formats
- **Epistemic Tiers**: A/B/C quality classification
- **Local-First**: No external APIs required, runs entirely on your hardware
- **Cross-Session**: Persistent memory across agent restarts

## Quick Start

```bash
# Install
pip install amem

# Set up Ollama (required for embeddings)
ollama pull nomic-embed-text

# Use in your agent
from amem import MemoryManager

mm = MemoryManager()

# Store a memory
note, status = mm.remember(
    "CVE-2024-3094 is a backdoor in XZ Utils discovered in March 2024",
    domain="security_ops"
)

# Retrieve by semantic similarity
results = mm.recall("XZ backdoor vulnerability", k=5)

# Fast entity lookup
apt28_notes = mm.recall_actor("APT28", k=10)
cve_notes = mm.recall_cve("CVE-2024-3094")

# Get formatted context for prompts
context = mm.get_context("threat actor activity", k=10)

# Synthesize answers from memories (Phase 7)
result = mm.synthesize(
    "What do we know about XZ backdoor?",
    format="synthesized_brief"  # or "direct_answer", "timeline_analysis", "relationship_map"
)
print(result["synthesis"]["summary"])
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         MemoryManager                        │
├──────────────┬──────────────┬──────────────┬────────────────┤
│ MemoryStore  │NoteConstructor│EntityIndexer │VectorRetriever │
│  (JSONL)     │  (Enrichment) │  (Index)     │  (Search)      │
├──────────────┴──────────────┴──────────────┴────────────────┤
│                    LanceDB Vector Store                      │
└─────────────────────────────────────────────────────────────┘
```

## Installation

### Requirements

- Python 3.10+
- Ollama (for local embeddings)

### From PyPI

```bash
pip install amem
```

### From Source

```bash
git clone https://github.com/rolandpg/amem.git
cd amem
pip install -e ".[dev]"
```

### Ollama Setup

A-MEM uses Ollama for generating embeddings locally:

```bash
# Install Ollama (macOS/Linux)
curl -fsSL https://ollama.com/install.sh | sh

# Pull the embedding model
ollama pull nomic-embed-text

# Start Ollama server
ollama serve
```

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `AMEM_DATA_DIR` | `~/.amem` | Data storage location |
| `AMEM_OLLAMA_URL` | `http://localhost:11434` | Ollama server URL |
| `AMEM_EMBEDDING_MODEL` | `nomic-embed-text` | Embedding model name |

## API Reference

### MemoryManager

Primary interface for all memory operations.

#### `remember(content, source_type="conversation", source_ref="", domain="general")`

Store a new memory note.

**Parameters:**
- `content` (str): The text content to remember
- `source_type` (str): Type of source (conversation, task_output, observation)
- `source_ref` (str): Reference to source (session_id, task_id)
- `domain` (str): Domain classification (security_ops, project, personal, research)

**Returns:** `(MemoryNote, str)` - The created note and status

#### `recall(query, domain=None, k=10, include_links=True)`

Retrieve memories by semantic similarity.

**Parameters:**
- `query` (str): Natural language query
- `domain` (str, optional): Filter by domain
- `k` (int): Number of results
- `include_links` (bool): Include linked notes

**Returns:** `List[MemoryNote]`

#### `recall_cve(cve_id, k=5)` / `recall_actor(name, k=5)` / `recall_tool(name, k=5)`

Fast entity-based retrieval.

#### `get_context(query, domain=None, k=10, token_budget=4000)`

Get formatted context string for prompt injection.

### MemoryNote Schema

```python
{
    "id": "note_20240405_185046_1234",
    "content": {
        "raw": "Full text content",
        "source_type": "conversation",
        "source_ref": "session_abc123"
    },
    "semantic": {
        "context": "One-sentence summary",
        "keywords": ["keyword1", "keyword2"],
        "tags": ["security", "cve"],
        "entities": ["cve-2024-3094", "apt28"]
    },
    "embedding": {
        "vector": [0.1, 0.2, ...],  # 768 dimensions
        "model": "nomic-embed-text"
    },
    "links": {
        "related": ["note_123", "note_456"],
        "superseded_by": None,
        "supersedes": []
    },
    "metadata": {
        "access_count": 0,
        "confidence": 1.0,
        "domain": "security_ops",
        "tier": "A"  # A=authoritative, B=operational, C=support
    }
}
```

## Development

```bash
# Clone repository
git clone https://github.com/rolandpg/amem.git
cd amem

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run specific test
pytest tests/test_memory_manager.py -v

# Format code
black src/amem/
ruff check src/amem/

# Type checking
mypy src/amem/
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=amem --cov-report=html

# Run specific phase tests
pytest tests/test_phase_1.py -v  # Entity indexing
pytest tests/test_phase_7.py -v  # Synthesis layer
```

## Roadmap

- [x] Phase 1: Core storage and retrieval
- [x] Phase 2: Entity extraction and indexing
- [x] Phase 3: Note linking and relationships
- [ ] Phase 4: Knowledge graph integration
- [ ] Phase 5: Synthesis layer (RAG-as-answer)
- [ ] Phase 6: Multi-agent memory sharing
- [ ] Phase 7: Distributed memory sync

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see [LICENSE](LICENSE) file

## Acknowledgments

- Built for the OpenClaw agent ecosystem
- Inspired by Zettelkasten note-taking methodology
- Embeddings powered by [Ollama](https://ollama.com)
- Vector storage by [LanceDB](https://lancedb.com)

## Support

- Documentation: https://github.com/rolandpg/amem/tree/main/docs
- Issues: https://github.com/rolandpg/amem/issues
- Discussions: https://github.com/rolandpg/amem/discussions
