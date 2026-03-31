---
name: vector-recall
description: Cross-session semantic memory available to all agents via mm.recall(query) and mm.get_context(query). Searches 36+ historical notes using Nomic embeddings.
category: memory
created: 2026-03-31T18:40:00
version: 1.0.0
agentScope: any
---

# Vector Recall — Cross-Session Memory

**Available to: any agent or subagent**

## What It Does

Provides semantic recall across all sessions. Any agent — main, subagent, or ACP harness — can query historical memory without needing to rebuild context.

## How to Load

```python
import sys
sys.path.insert(0, '/home/rolandpg/.openclaw/workspace')

from memory_init import memory_manager
mm = memory_manager()  # already initialized in main agent boot
```

Or in a subagent/session:
```python
import sys
sys.path.insert(0, '/home/rolandpg/.openclaw/workspace')
from memory.memory_manager import get_memory_manager
mm = get_memory_manager()
```

## Core Methods

| Method | Use | Returns |
|--------|-----|---------|
| `mm.recall(query, k=5)` | Semantic search across all sessions | List[MemoryNote] |
| `mm.get_context(query, k=5)` | Formatted string for context injection | str |
| `mm.remember(text, domain='security_ops')` | Save a new cross-session memory | MemoryNote |
| `mm.get_recent(limit=10)` | Most recent memories | List[MemoryNote] |

## When to Use

**Before answering questions about:**
- Prior decisions, discussions, or agreements
- Technical implementations from past sessions
- Project history, key learnings, lessons learned
- Threat actor research already done
- Financial analysis or deal tracking

**After completing:**
- A significant decision or direction change
- A build, deployment, or configuration change
- Any work you want future-you to know about
- A mistake and what you learned from it

## Domain Tags

Filter by domain for focused recall:
- `security_ops` — CTI, security research, tool builds
- `financial` — MSSP M&A, PE deals, market analysis
- `social_media` — X.com, content performance, engagement
- `project` — Infrastructure, tool changes
- `research` — Deep dives, briefings

## Example: Recall Before Answering

```python
# Main agent boot — before answering anything about past work
results = mm.recall('how did we handle the memory recall problem')
if results:
    ctx = mm.get_context('how did we handle the memory recall problem')
    # Inject ctx into your response context
```

## Example: Remember After Building

```python
# After building something significant
mm.remember(
    'Built vector memory using LanceDB + Nomic embeddings. '
    'Fixed LanceDB pyarrow schema for v0.30. Lowered threshold to 0.30.',
    domain='security_ops'
)
```

## Stats

- 36+ real notes indexed (Volt Typhoon, MSSP market, Qualys, etc.)
- 11 bad placeholder notes archived
- Embedding model: `nomic-embed-text-v2-moe` (768 dims, local)
- Similarity threshold: 0.30

## Limitations

- LanceDB schema was migrated to pyarrow for v0.30 compatibility
- New notes require LLM call for semantic enrichment (nemotron-3-nano) — ~5s latency
- Similarity threshold of 0.30 is deliberately low; increase to 0.5+ for precision tasks

## References

- Schema: `workspace/memory/note_schema.py`
- Store: `workspace/memory/memory_store.py`
- Vector retriever: `workspace/memory/vector_retriever.py`
- Embeddings: `workspace/memory/embedding_utils.py`
