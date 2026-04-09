---
title: "Query What Tools an APT Group Uses"
description: "Use recall(), synthesize(), and traverse_graph() to discover tool usage relationships for threat actor groups."
diataxis_type: "how-to"
audience: "CTI analysts querying stored intelligence, agent developers building CTI tooling"
tags: [recall, synthesize, traverse-graph, relationship-map, apt, tools, cti]
last_updated: "2026-04-09"
version: "2.0.0"
---

# Query What Tools an APT Group Uses

Retrieve tool-usage relationships for a threat actor using blended vector + graph retrieval, synthesis, and direct graph traversal.

## Prerequisites

- ZettelForge with stored CTI data (see [Store Threat Actor](store-threat-actor.md))
- Embedding and LLM models available (download automatically on first use)

## Steps

### 1. Initialize MemoryManager

```python
from zettelforge.memory_manager import MemoryManager

mm = MemoryManager()
```

### 2. Recall notes related to a threat actor's tools

```python
notes = mm.recall(
    query="What tools does APT28 use?",
    domain="cti",
    k=10
)

for note in notes:
    print(f"  [{note.metadata.confidence:.2f}] {note.content.raw[:100]}")
```

> [!NOTE]
> `recall()` uses intent classification internally. A relational query like "what tools does X use" triggers higher graph traversal weight in blended retrieval, surfacing notes connected via `USES_TOOL` edges.

### 3. Synthesize a relationship map

```python
result = mm.synthesize(
    query="What tools does APT28 use?",
    format="relationship_map",
    k=10
)

print(result["synthesis"]["summary"])

for source in result.get("sources", []):
    print(f"  Source: {source['note_id']} (confidence: {source['confidence']})")
```

Available synthesis formats:

| Format | Use case |
|--------|----------|
| `direct_answer` | Short factual response |
| `synthesized_brief` | Paragraph summary with sources |
| `timeline_analysis` | Chronological reconstruction |
| `relationship_map` | Entity relationship summary |

### 4. Traverse the graph directly

For structured relationship data without LLM synthesis:

```python
graph = mm.traverse_graph(
    start_type="actor",
    start_value="apt28",
    max_depth=2
)

tools = [
    entry for entry in graph
    if entry.get("relationship") == "USES_TOOL"
]

for t in tools:
    print(f"  Tool: {t['entity_value']}")
```

### 5. Get direct entity relationships

For single-hop lookups without full traversal:

```python
relationships = mm.get_entity_relationships("actor", "apt28")

tool_rels = [r for r in relationships if r["relationship"] == "USES_TOOL"]
cve_rels = [r for r in relationships if r["relationship"] == "EXPLOITS_CVE"]

print(f"APT28 tools: {[r['to_value'] for r in tool_rels]}")
print(f"APT28 CVEs:  {[r['to_value'] for r in cve_rels]}")
```

### 6. Use entity-specific fast lookup

```python
# All notes mentioning APT28
actor_notes = mm.recall_actor("APT28", k=5)

# All notes mentioning Cobalt Strike
tool_notes = mm.recall_tool("Cobalt Strike", k=5)

# Cross-reference: which notes mention both?
actor_ids = {n.id for n in actor_notes}
tool_ids = {n.id for n in tool_notes}
overlap = actor_ids & tool_ids

print(f"Notes mentioning both APT28 and Cobalt Strike: {len(overlap)}")
```

> [!TIP]
> `recall_actor()`, `recall_tool()`, and `recall_cve()` use the entity index for O(1) lookup. They bypass vector search entirely and are significantly faster for known-entity queries.

### 7. Compare tool usage across actors

```python
actors = ["apt28", "lazarus group", "volt typhoon"]

for actor in actors:
    rels = mm.get_entity_relationships("actor", actor)
    tools = [r["to_value"] for r in rels if r["relationship"] == "USES_TOOL"]
    print(f"  {actor}: {tools}")
```

> [!WARNING]
> `synthesize()` requires the LLM (loaded in-process by default). If the LLM is unavailable, use `traverse_graph()` or `get_entity_relationships()` for graph-only queries that do not require generation.

## LLM Quick Reference

**Task**: Query tool-usage relationships for threat actors from stored CTI intelligence.

**Semantic query**: `mm.recall("What tools does APT28 use?", domain="cti", k=10)` returns `List[MemoryNote]`. Uses blended vector + graph retrieval with intent-aware weighting.

**Synthesis**: `mm.synthesize("What tools does APT28 use?", format="relationship_map", k=10)` returns `Dict` with `synthesis.summary`, `sources[]`, and `metadata`. Requires running LLM.

**Graph traversal**: `mm.traverse_graph("actor", "apt28", max_depth=2)` returns `List[Dict]` with `entity_type`, `entity_value`, `relationship`, `depth` fields. No LLM required.

**Direct relationships**: `mm.get_entity_relationships("actor", "apt28")` returns single-hop neighbors as `List[Dict]` with `relationship`, `to_type`, `to_value`.

**Entity index**: `mm.recall_actor("APT28")`, `mm.recall_tool("Cobalt Strike")`, `mm.recall_cve("CVE-2024-3094")` provide O(1) entity-indexed lookups returning `List[MemoryNote]`.

**Alias handling**: All query methods resolve aliases automatically. "Fancy Bear" queries return APT28 results.

**Synthesis formats**: `direct_answer` (short), `synthesized_brief` (paragraph), `timeline_analysis` (chronological), `relationship_map` (entity graph summary). Default is `direct_answer`.
