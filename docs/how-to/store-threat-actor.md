---
title: "Store Threat Intelligence About an Actor"
description: "Use remember() with automatic entity extraction to store threat actor intelligence and populate the knowledge graph."
diataxis_type: "how-to"
audience: "CTI analysts, security engineers integrating ZettelForge into workflows"
tags: [remember, entity-extraction, threat-actor, knowledge-graph, cti]
last_updated: "2026-04-09"
version: "2.0.0"
---

# Store Threat Intelligence About an Actor

Store threat actor intelligence using `remember()`. ZettelForge automatically extracts entities (actors, tools, CVEs, campaigns), resolves aliases, and populates the knowledge graph with inferred relationships.

## Prerequisites

- ZettelForge installed (`pip install zettelforge`)
- Embedding and LLM models available (download automatically on first use)
- TypeDB running (optional; falls back to JSONL graph)

## Steps

### 1. Create a MemoryManager instance

```python
from zettelforge.memory_manager import MemoryManager

mm = MemoryManager()
```

To use custom storage paths:

```python
mm = MemoryManager(
    jsonl_path="/data/zettelforge/notes.jsonl",
    lance_path="/data/zettelforge/lance"
)
```

### 2. Store threat actor intelligence with `remember()`

```python
content = (
    "APT28 (Fancy Bear) deployed Cobalt Strike beacons against NATO-aligned "
    "government networks in Q1 2026. The campaign exploited CVE-2024-3094, "
    "a critical backdoor in xz-utils, for initial access. Post-exploitation "
    "relied on Mimikatz for credential harvesting."
)

note, status = mm.remember(
    content=content,
    source_type="report",
    source_ref="mandiant-apt28-q1-2026",
    domain="cti"
)

print(f"Note ID: {note.id}")
print(f"Status: {status}")
print(f"Created: {note.created_at}")
```

> [!NOTE]
> The `domain="cti"` parameter triggers CTI-specific entity extraction and causal triple extraction (MAGMA-style) for richer graph edges.

### 3. Verify extracted entities

```python
from zettelforge.entity_indexer import EntityIndexer

indexer = EntityIndexer()
entities = indexer.extractor.extract_all(content)

for entity_type, values in entities.items():
    print(f"  {entity_type}: {values}")
```

Expected output:

```
  actor: ['apt28']
  tool: ['cobalt strike', 'mimikatz']
  cve: ['CVE-2024-3094']
```

> [!TIP]
> Aliases resolve automatically. "Fancy Bear" in the content resolves to "apt28" before indexing. See [Resolve Aliases](resolve-aliases.md) for details.

### 4. Check the knowledge graph

```python
relationships = mm.get_entity_relationships("actor", "apt28")

for rel in relationships:
    print(f"  {rel['relationship']}: {rel['to_type']}:{rel['to_value']}")
```

Expected output:

```
  USES_TOOL: tool:cobalt strike
  USES_TOOL: tool:mimikatz
  EXPLOITS_CVE: cve:CVE-2024-3094
  MENTIONED_IN: note:<note_id>
```

### 5. Traverse the graph from the actor

```python
graph = mm.traverse_graph(
    start_type="actor",
    start_value="apt28",
    max_depth=2
)

for entry in graph:
    print(f"  depth={entry.get('depth', 0)} "
          f"{entry['entity_type']}:{entry['entity_value']} "
          f"via {entry.get('relationship', 'root')}")
```

> [!WARNING]
> If TypeDB is not running, graph traversal uses the JSONL fallback. Relationship data is identical, but query performance degrades above ~50,000 edges.

### 6. Store multiple facts with extraction pipeline

For richer storage that deduplicates against existing notes, use `remember_with_extraction()`:

```python
results = mm.remember_with_extraction(
    content=(
        "Lazarus Group used Cobalt Strike and a custom loader called "
        "DTrack to target cryptocurrency exchanges in March 2026. "
        "CISA advisory AA26-078A links the campaign to CVE-2024-3094."
    ),
    domain="cti",
    min_importance=3,
    max_facts=5
)

for note, status in results:
    if note:
        print(f"  [{status}] {note.id}: {note.content.raw[:80]}")
```

## LLM Quick Reference

**Task**: Store threat actor intelligence with automatic entity extraction and knowledge graph population.

**Primary method**: `mm.remember(content, source_type="report", source_ref="...", domain="cti")` returns `(MemoryNote, str)`. Entities (actors, tools, CVEs, campaigns, assets) are extracted automatically, aliases resolved, and graph edges created.

**Entity extraction pipeline**: Content passes through `EntityIndexer.extractor.extract_all()` which identifies entity types. Each entity goes through `AliasResolver.resolve()` before indexing and graph storage.

**Graph edges created automatically**: `USES_TOOL` (actor-tool), `EXPLOITS_CVE` (actor-cve, tool-cve), `TARGETS_ASSET` (actor-asset, tool-asset), `CONDUCTS_CAMPAIGN` (actor-campaign), `MENTIONED_IN` (all entities-note).

**Causal triples**: For `domain="cti"` notes or content >200 chars, LLM-based causal triple extraction runs, adding richer semantic edges to the graph.

**Two-phase alternative**: `mm.remember_with_extraction(content, domain="cti", min_importance=3, max_facts=5)` extracts discrete facts, compares each against existing notes, and returns ADD/UPDATE/DELETE/NOOP decisions per fact.

**Alias resolution**: "Fancy Bear", "Pawn Storm", "Sofacy", "Forest Blizzard" all resolve to "apt28". Works via TypeDB `alias-of` relations with JSONL fallback.

**Key config**: `domain="cti"` activates CTI entity extraction. `source_type` accepts "conversation", "report", "task_output". `source_ref` is a free-text provenance string.
