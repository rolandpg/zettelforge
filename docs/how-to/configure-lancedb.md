---
title: "Tune LanceDB Vector Search"
description: "Configure embedding models, IVF_PQ index parameters, similarity thresholds, and entity boost for optimal CTI retrieval."
diataxis_type: "how-to"
audience: "Platform engineers optimizing retrieval performance, CTI analysts tuning search quality"
tags: [lancedb, vector-search, embeddings, configuration, tuning, retrieval]
last_updated: "2026-04-09"
version: "2.0.0"
---

# Tune LanceDB Vector Search

Configure LanceDB vector search for optimal retrieval quality. Adjust embedding model, index parameters, similarity threshold, and entity boost to balance precision and recall for your CTI workload.

## Prerequisites

- ZettelForge installed (`pip install zettelforge`)
- Ollama running with an embedding model
- Stored notes to test against (see [Store Threat Actor](store-threat-actor.md))

## Steps

### 1. Configure the embedding model

Edit `config.yaml`:

```yaml
embedding:
  url: http://127.0.0.1:11434
  model: nomic-embed-text-v2-moe:latest
  dimensions: 768
```

Or set via environment variables:

```bash
export AMEM_EMBEDDING_URL=http://127.0.0.1:11434
export AMEM_EMBEDDING_MODEL=nomic-embed-text-v2-moe:latest
```

Supported configurations:

| Provider | URL | Model | Dimensions |
|----------|-----|-------|------------|
| Ollama (default) | `http://127.0.0.1:11434` | `nomic-embed-text-v2-moe:latest` | 768 |
| Ollama (alternative) | `http://127.0.0.1:11434` | `nomic-embed-text` | 768 |
| llama.cpp server | `http://127.0.0.1:8081` | `nomic-embed-text-v2-moe.gguf` | 768 |
| Remote GPU | `http://gpu-box:11434` | `nomic-embed-text-v2-moe:latest` | 768 |

> [!WARNING]
> Changing the embedding model after data has been indexed requires a full re-index. Existing vectors become incompatible with new model embeddings. Run `python scripts/rebuild_index.py` after changing models.

### 2. Verify embedding connectivity

```python
from zettelforge.vector_memory import get_embedding

vector = get_embedding("APT28 uses Cobalt Strike for command and control")
print(f"Embedding dimensions: {len(vector)}")
print(f"First 5 values: {vector[:5]}")
```

Expected: `Embedding dimensions: 768`

### 3. Configure retrieval parameters

Edit the `retrieval` section of `config.yaml`:

```yaml
retrieval:
  default_k: 10
  similarity_threshold: 0.25
  entity_boost: 2.5
  max_graph_depth: 2
```

Parameter reference:

| Parameter | Default | Range | Effect |
|-----------|---------|-------|--------|
| `default_k` | `10` | 1-100 | Max results returned per query |
| `similarity_threshold` | `0.25` | 0.0-1.0 | Minimum cosine similarity to include a result |
| `entity_boost` | `2.5` | 0.0-10.0 | Multiplicative boost per overlapping entity between query and note |
| `max_graph_depth` | `2` | 1-5 | Hops to traverse in knowledge graph during blended retrieval |

### 4. Tune for high precision (fewer, more relevant results)

```yaml
retrieval:
  default_k: 5
  similarity_threshold: 0.50
  entity_boost: 3.0
  max_graph_depth: 1
```

```python
from zettelforge.memory_manager import MemoryManager

mm = MemoryManager()
notes = mm.recall("APT28 Cobalt Strike C2", domain="cti", k=5)
print(f"High-precision results: {len(notes)}")
```

### 5. Tune for high recall (cast a wide net)

```yaml
retrieval:
  default_k: 25
  similarity_threshold: 0.10
  entity_boost: 1.5
  max_graph_depth: 3
```

```python
notes = mm.recall("APT28 Cobalt Strike C2", domain="cti", k=25)
print(f"High-recall results: {len(notes)}")
```

> [!TIP]
> Start with the defaults (`similarity_threshold: 0.25`, `entity_boost: 2.5`). Lower the threshold only if relevant notes are being filtered out. Raise entity_boost if entity-specific queries return too much noise from semantically similar but entity-unrelated notes.

### 6. Understand IVF_PQ index settings

These defaults are optimal for collections up to ~1M notes. No manual tuning is needed below 10,000 notes.

> [!NOTE]
> IVF_PQ index creation happens automatically when the LanceDB table exceeds a size threshold. You do not need to trigger index builds manually.

### 7. Configure the data directory

```yaml
storage:
  data_dir: ~/.amem
```

Or:

```bash
export AMEM_DATA_DIR=/data/zettelforge
```

LanceDB stores its data at `{data_dir}/lance/`. The directory structure:

```
~/.amem/
  notes.jsonl          # Note metadata
  lance/               # LanceDB vector index
  kg_nodes.jsonl       # Knowledge graph nodes
  kg_edges.jsonl       # Knowledge graph edges
  entity_aliases.json  # Local alias mappings
```

### 8. Rebuild the index after configuration changes

```bash
python scripts/rebuild_index.py
```

> [!WARNING]
> Rebuilding the index re-embeds all notes. This requires the embedding server to be running and takes approximately 1 second per 100 notes on local Ollama.

## LLM Quick Reference

**Task**: Configure and tune LanceDB vector search for CTI retrieval workloads.

**Embedding config**: `embedding.url` (default `http://127.0.0.1:11434`), `embedding.model` (default `nomic-embed-text-v2-moe:latest`), `embedding.dimensions` (default 768). Env overrides: `AMEM_EMBEDDING_URL`, `AMEM_EMBEDDING_MODEL`.

**Retrieval config**: `retrieval.default_k` (10), `retrieval.similarity_threshold` (0.25, range 0.0-1.0), `retrieval.entity_boost` (2.5, multiplicative per overlapping entity), `retrieval.max_graph_depth` (2, hops in KG traversal).

**High precision preset**: `default_k: 5`, `similarity_threshold: 0.50`, `entity_boost: 3.0`, `max_graph_depth: 1`.

**High recall preset**: `default_k: 25`, `similarity_threshold: 0.10`, `entity_boost: 1.5`, `max_graph_depth: 3`.

**IVF_PQ defaults**: 256 partitions, 16 sub-vectors (768 dims / 16 = 48 dims per sub-vector). Auto-created when table exceeds threshold. No manual trigger needed.

**Storage**: `storage.data_dir` (default `~/.amem`). Env override: `AMEM_DATA_DIR`. LanceDB data at `{data_dir}/lance/`.

**Re-index**: `python scripts/rebuild_index.py` after changing embedding model. Required because vector dimensions/space change with model.
