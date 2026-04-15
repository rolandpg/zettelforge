---
name: zettelforge
description: "ZettelForge CTI Memory — Store, recall, and synthesize threat intelligence. Use when agents need persistent CTI memory, threat actor attribution, CVE lookups, STIX graph traversal, or RAG synthesis over threat reports. Triggers on: remember intel, recall threats, what tools does X use, CVE lookup, threat actor research, synthesize brief."
tools:
  - zettelforge_remember
  - zettelforge_recall
  - zettelforge_synthesize
  - zettelforge_entity
  - zettelforge_graph
  - zettelforge_stats
  - zettelforge_sync
---

# ZettelForge: CTI Agentic Memory

Persistent memory system for cyber threat intelligence. 75% accuracy on CTI queries, 111ms p50 latency.

## When to use this skill

- Storing threat intelligence from reports, incidents, or conversations
- Recalling what we know about a threat actor, CVE, tool, or campaign
- Synthesizing briefs from accumulated intelligence
- Looking up entity relationships (who uses what, who targets what)
- Traversing the STIX 2.1 knowledge graph
- Syncing from OpenCTI

## Quick reference

### Store intel
```python
from zettelforge import MemoryManager
mm = MemoryManager()
note, status = mm.remember("APT28 uses Cobalt Strike via CVE-2024-1111", domain="cti")
```

### Search memory
```python
results = mm.recall("What tools does APT28 use?", k=10)
for r in results:
    print(f"{r.id}: {r.content.raw[:100]}")
```

### Entity lookup (fast, O(1))
```python
mm.recall_actor("APT28")           # or "Fancy Bear" — aliases resolve automatically
mm.recall_cve("CVE-2024-3094")
mm.recall_tool("cobalt-strike")
```

### Synthesize answer
```python
result = mm.synthesize("Summarize APT28 activity", format="synthesized_brief")
# formats: direct_answer, synthesized_brief, timeline_analysis, relationship_map
```

### Graph traversal
```python
paths = mm.traverse_graph("actor", "apt28", max_depth=2)
# APT28 → USES_TOOL → cobalt-strike → EXPLOITS_CVE → CVE-2024-1111
```

### Ingest report (auto-chunks)
```python
results = mm.remember_report(content="Full report text...", source_url="https://...", domain="cti")
```

### Two-phase extraction (selective, deduplicating)
```python
results = mm.remember_with_extraction("APT28 dropped DROPBEAR, now uses edge devices", domain="cti")
# Returns: [(<MemoryNote>, "added"), (<MemoryNote>, "updated"), ...]
```

### OpenCTI sync
```python
from zettelforge.opencti_sync import sync_opencti
stats = sync_opencti(mm, limit=50)  # Pull latest from OpenCTI
```

## MCP tools available

If the ZettelForge MCP server is configured, use these tools directly:

| Tool | What it does |
|------|-------------|
| `zettelforge_remember` | Store CTI text (extracts entities, updates graph) |
| `zettelforge_recall` | Blended search (vector + graph + reranking) |
| `zettelforge_synthesize` | RAG synthesis in 4 formats |
| `zettelforge_entity` | Fast entity lookup by type + value |
| `zettelforge_graph` | STIX knowledge graph traversal |
| `zettelforge_stats` | Memory system statistics |
| `zettelforge_sync` | Pull from OpenCTI |

## Architecture

- Hybrid: TypeDB (STIX 2.1 ontology) + LanceDB (vectors)
- Zero external AI: fastembed (embeddings) + llama-cpp-python (LLM)
- 10 entity types: CVE, actor, tool, campaign, person, location, org, event, activity, temporal
- Cross-encoder reranking (ms-marco-MiniLM)
- 36 CTI aliases seeded (APT28/Fancy Bear/Strontium, etc.)

## Configuration

```yaml
# config.yaml
backend: jsonl          # or typedb
embedding:
  provider: fastembed
llm:
  provider: local
```
