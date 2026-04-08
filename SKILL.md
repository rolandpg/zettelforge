---
name: zettelforge
description: ZettelForge (Agentic Memory System) - A production-grade agent memory system with vector search, knowledge graph, entity indexing, and synthesis layer. Use this skill when the user wants to store, retrieve, or synthesize information across sessions, build persistent agent memory, or implement RAG-as-answer capabilities. Automatically triggers on memory-related requests, persistence needs, cross-session recall, or knowledge management tasks.
---

# ZettelForge: Agentic Memory System

A production-grade memory system for AI agents. Store, retrieve, and synthesize information with vector search, knowledge graphs, and entity-aware linking.

## ⚠️ Known Issues (2026-04-08)

**Critical**: Vector retrieval via LanceDB is non-functional. The following features are **currently broken**:
- ❌ Synthesis layer (`mm.synthesize()`) - returns "No answer" due to empty context retrieval
- ❌ Semantic similarity search (vector retrieval returns empty)
- ❌ Temporal reasoning in synthesis
- ❌ Multi-hop graph traversal in synthesis

**Working features**:
- ✅ JSONL note storage
- ✅ Entity extraction and indexing
- ✅ Entity-based recall (`recall_actor`, `recall_cve`)
- ✅ Intent classification (routes correctly)

**Fix in progress**: See `research/zettelforge_synthesis_fix_plan.md`

---

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

**⚠️ WARNING**: Synthesis layer is currently non-functional due to broken vector retrieval. The following formats are documented but do not work:

- `direct_answer`: Concise answer with sources **[BROKEN - returns "No answer"]**
- `synthesized_brief`: Thematic analysis **[BROKEN]**
- `timeline_analysis`: Chronological events **[BROKEN]**
- `relationship_map`: Entity connections **[BROKEN]**

**Use `mm.recall()` or `mm.recall_actor()` instead for working retrieval.**

## Configuration

Environment variables:
```bash
AMEM_DATA_DIR=/path/to/data    # Default: ~/.amem
AMEM_OLLAMA_URL=http://localhost:11434
AMEM_EMBEDDING_MODEL=nomic-embed-text
```

## MAGMA Extensions (2026-04)

Four improvements from MAGMA/Kumiho research:

### 1. Causal Triple Extraction
LLM-based extraction of causal relationships from notes:
```python
from zettelforge.note_constructor import NoteConstructor
constructor = NoteConstructor()
triples = constructor.extract_causal_triples(text, note_id)
edges = constructor.store_causal_edges(triples, note_id)
```
Relations: `causes`, `enables`, `targets`, `uses`, `exploits`, `attributed_to`, `related_to`

### 2. Temporal Graph
Time-based indexing and queries:
```python
from zettelforge.knowledge_graph import get_knowledge_graph
kg = get_knowledge_graph()
timeline = kg.get_entity_timeline("actor", "apt28")
changes = kg.get_changes_since("2024-01-01")
```
Temporal edge types: `SUPERSEDES`, `TEMPORAL_BEFORE`, `TEMPORAL_AFTER`

### 3. Intent Classifier
Adaptive query routing at recall time:
```python
from zettelforge.intent_classifier import get_intent_classifier
classifier = get_intent_classifier()
intent, meta = classifier.classify("What changed since May 2024?")
policy = classifier.get_traversal_policy(intent)
```
Intent types: `factual`, `temporal`, `relational`, `causal`, `exploratory`

### 4. Adaptive Recall
`mm.recall()` now routes based on intent:
- Factual → entity index
- Temporal → temporal graph
- Relational/Causal → graph traversal
- Exploratory → vector search

## CTI Platform Integration (v1.2.0)

Bi-directional sync with Django CTI database:
```python
from zettelforge import get_cti_connector, import_cti_to_memory, unified_recall

# Connect to CTI platform
connector = get_cti_connector()

# Search CTI platform
actors = connector.search_cti("APT28", entity_type="actor")
cves = connector.search_cti("CVE-2024", entity_type="cve")

# Import CTI to memory
import_cti_to_memory(mm, query="APT28", entity_type="actor")

# Unified recall
results = unified_recall(mm, "APT28")
# results = {"memory": [...], "cti": [...]}
```

**CTI Stats:** 30 actors, 1559 CVEs, 90K+ IOCs accessible

## Proactive Context Injection (v1.2.0)

Auto-preload relevant context before agent tasks:
```python
from zettelforge import ContextInjector, get_cti_connector, get_memory_manager

# Setup
injector = ContextInjector(memory_manager=mm, cti_connector=cti)

# Before task - returns relevant memory + CTI
context = injector.inject_context("Analyze CVE-2024-1111")

# Inject into LLM prompt
enhanced_prompt = injector.inject_into_prompt(task, base_prompt)
```

**Task Classification:** cve_analysis, threat_actor_research, incident_response, malware_analysis, planning

## Sigma Rule Generation (v1.3.0)

Generate detection rules from CTI IOCs:
```python
from zettelforge import get_cti_connector, get_sigma_generator

cti = get_cti_connector()
sigma = get_sigma_generator(cti)

# Generate rules for a threat actor
rules = sigma.generate_from_actor("microsoft", min_confidence="LOW")

# Export to Sigma YAML
yaml_out = sigma.export_yaml(rules)

# Export to Sentinel KQL
kql = sigma.export_sentinel(rules)
```

**Output Formats:** Sigma YAML, Microsoft Sentinel KQL

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
