# Implementation Plan: Causal Graph (Feature 3)

**Date:** 2026-04-15
**Estimated effort:** 3-4 days
**Branch:** `feat/causal-graph`

## Goal

Add typed causal edges to the community knowledge graph, route CAUSAL-intent queries to a causal-only traversal, and expose a `provenance_chain()` that traces entity-to-entity causal paths back to source notes.

## Architecture Decisions

### AD-1: `edge_type` is community-only

The JSONL `KnowledgeGraph` gains an `edge_type` metadata field on every edge (`"heuristic"`, `"causal"`, `"temporal"`). Enterprise TypeDB already types edges by relation name via `RELATION_MAP` in `typedb_client.py` -- it does not need `edge_type`. Document this divergence in `ARCHITECTURE.md`.

### AD-2: Causal chain traces entity-to-entity, not note-to-note

`Links.causal_chain` today stores note IDs, but notes do not have direct causal edges -- their entities do. The provenance chain returns:

```
source_note -> entity -> CAUSAL_EDGE -> target_entity -> target_notes
```

Each step in the chain is a dict: `{note_id, entity_type, entity_value, relation, target_entity_type, target_entity_value, target_note_ids}`.

### AD-3: BFS cap at 50 nodes visited total

The existing `GraphRetriever._bfs_collect` has no fan-out limit. High-fan-out entities like "phishing" will explode at depth 3. Fix: cap `visited` set at 50 nodes total, independent of depth. This is a global guard, not per-entity.

### AD-4: Correct add_edge count

There are **17** `kg.add_edge()` call sites in `_update_knowledge_graph()` (lines 586-650 of `memory_manager.py`), plus 1 `MENTIONED_IN` per entity. All 17 get `edge_type="heuristic"` in their properties.

## Tasks

### Task 1: Add `edge_type` to edge properties (0.5 day)

**Files:**
- `src/zettelforge/knowledge_graph.py`
- `src/zettelforge/memory_manager.py`
- `src/zettelforge/note_constructor.py`

**Steps:**

1. In `KnowledgeGraph.add_edge()`, add `edge_type` to the edge dict if present in `properties`. Default to `"heuristic"` if not provided.

```python
# knowledge_graph.py — add_edge(), after creating the edge dict
edge = {
    "edge_id": edge_id,
    "from_node_id": from_id,
    "to_node_id": to_id,
    "relationship": relationship,
    "edge_type": properties.pop("edge_type", "heuristic"),
    "properties": properties or {},
    "created_at": datetime.now().isoformat(),
    "updated_at": datetime.now().isoformat(),
}
```

2. In `_update_knowledge_graph()`, ensure all 17 `add_edge` calls pass `edge_type="heuristic"` via `edge_props`:

```python
edge_props = {
    "first_observed": now,
    "confidence": note.metadata.confidence,
    "edge_type": "heuristic",
}
```

3. In `note_constructor.py` `store_causal_edges()`, pass `edge_type="causal"`:

```python
kg.add_edge(
    from_type=from_type,
    from_value=subject,
    to_type=to_type,
    to_value=obj,
    relationship=relation,
    properties={
        "note_id": note_id,
        "source": "llm_extraction",
        "edge_type": "causal",
    },
)
```

4. Add `get_edges_by_type()` to `KnowledgeGraph`:

```python
def get_edges_by_type(self, node_id: str, edge_type: str) -> List[Dict]:
    """Return outgoing edges filtered by edge_type."""
    return [
        e for e in self._edges_from.get(node_id, [])
        if e.get("edge_type", "heuristic") == edge_type
    ]
```

**Test:**
```bash
python -m pytest tests/ -k "test_add_edge" -x
python -m pytest tests/ -k "test_knowledge_graph" -x
```

### Task 2: Causal-only traversal in GraphRetriever (1 day)

**Files:**
- `src/zettelforge/graph_retriever.py`

**Steps:**

1. Add `edge_type_filter` parameter to `_bfs_collect()`:

```python
def _bfs_collect(
    self,
    start_type: str,
    start_value: str,
    max_depth: int,
    best: Dict[str, ScoredResult],
    edge_type_filter: Optional[str] = None,
    max_visited: int = 200,
):
    # ...existing setup...
    while queue:
        if len(visited) >= max_visited:
            break
        current_id, depth, path = queue.pop(0)
        if current_id in visited:
            continue
        visited.add(current_id)
        # ...existing note collection...
        if depth >= max_depth:
            continue
        for edge in self.kg.get_outgoing_edges(current_id):
            # Filter by edge_type if specified
            if edge_type_filter and edge.get("edge_type", "heuristic") != edge_type_filter:
                continue
            to_id = edge["to_node_id"]
            # ...rest of BFS...
```

2. Add `retrieve_causal()` method:

```python
def retrieve_causal(
    self,
    query_entities: Dict[str, List[str]],
    max_depth: int = 3,
    max_visited: int = 50,
) -> List[ScoredResult]:
    """Retrieve notes reachable via causal edges only."""
    if not query_entities:
        return []
    best: Dict[str, ScoredResult] = {}
    for entity_type, values in query_entities.items():
        for entity_value in values:
            self._bfs_collect(
                entity_type, entity_value, max_depth, best,
                edge_type_filter="causal",
                max_visited=max_visited,
            )
    results = list(best.values())
    results.sort(key=lambda r: r.score, reverse=True)
    return results
```

3. Apply `max_visited=50` cap for causal traversal (AD-3). The general `retrieve_note_ids` keeps `max_visited=200` (existing behavior, just made explicit).

**Test:**
```bash
python -m pytest tests/ -k "test_graph_retriever" -x
```

### Task 3: Route CAUSAL intent to causal traversal (0.5 day)

**Files:**
- `src/zettelforge/memory_manager.py`

**Steps:**

1. In `recall()`, after intent classification, check for CAUSAL intent and use `retrieve_causal()`:

```python
if intent == QueryIntent.CAUSAL:
    graph_results = graph_retriever.retrieve_causal(
        query_entities=resolved, max_depth=3, max_visited=50
    )
else:
    graph_results = graph_retriever.retrieve_note_ids(
        query_entities=resolved, max_depth=2
    )
```

2. Import `QueryIntent` at the top of the CAUSAL branch (it is already imported via `get_intent_classifier`).

**Test:**
```bash
python -m pytest tests/ -k "test_recall" -x
```

### Task 4: `provenance_chain()` (1 day)

**Files:**
- `src/zettelforge/knowledge_graph.py`
- `src/zettelforge/memory_manager.py`

**Steps:**

1. Add `provenance_chain()` to `KnowledgeGraph`:

```python
def provenance_chain(
    self,
    start_type: str,
    start_value: str,
    max_depth: int = 3,
    max_visited: int = 50,
) -> List[Dict]:
    """
    Trace causal provenance: entity -> causal edges -> target entities -> notes.

    Returns list of chain steps:
    [
        {
            "entity_type": str, "entity_value": str,
            "relation": str,
            "target_type": str, "target_value": str,
            "source_note_ids": [str], "target_note_ids": [str],
            "depth": int,
        },
        ...
    ]
    """
    start_node_id = self._node_index.get(start_type, {}).get(start_value)
    if not start_node_id:
        return []

    visited = set()
    chain = []
    queue = [(start_node_id, 0)]

    while queue and len(visited) < max_visited:
        current_id, depth = queue.pop(0)
        if current_id in visited or depth > max_depth:
            continue
        visited.add(current_id)

        current_node = self._nodes.get(current_id)
        if not current_node or current_node["entity_type"] == "note":
            continue

        # Get note IDs that mention this entity
        source_notes = [
            e["to_node_id"] for e in self._edges_from.get(current_id, [])
            if self._nodes.get(e["to_node_id"], {}).get("entity_type") == "note"
            and e.get("relationship") == "MENTIONED_IN"
        ]
        source_note_ids = [
            self._nodes[nid]["entity_value"] for nid in source_notes
            if nid in self._nodes
        ]

        # Follow causal edges only
        for edge in self._edges_from.get(current_id, []):
            if edge.get("edge_type", "heuristic") != "causal":
                continue
            to_id = edge["to_node_id"]
            to_node = self._nodes.get(to_id)
            if not to_node or to_node["entity_type"] == "note":
                continue

            # Get target notes
            target_notes = [
                e["to_node_id"] for e in self._edges_from.get(to_id, [])
                if self._nodes.get(e["to_node_id"], {}).get("entity_type") == "note"
                and e.get("relationship") == "MENTIONED_IN"
            ]
            target_note_ids = [
                self._nodes[nid]["entity_value"] for nid in target_notes
                if nid in self._nodes
            ]

            chain.append({
                "entity_type": current_node["entity_type"],
                "entity_value": current_node["entity_value"],
                "relation": edge.get("relationship", ""),
                "target_type": to_node["entity_type"],
                "target_value": to_node["entity_value"],
                "source_note_ids": source_note_ids,
                "target_note_ids": target_note_ids,
                "depth": depth,
            })

            if to_id not in visited:
                queue.append((to_id, depth + 1))

    return chain
```

2. Expose `provenance_chain()` on `MemoryManager`:

```python
def provenance_chain(
    self, entity_type: str, entity_value: str, max_depth: int = 3
) -> List[Dict]:
    """Trace causal provenance for an entity through the knowledge graph."""
    kg = get_knowledge_graph()
    canonical = self.resolver.resolve(entity_type, entity_value)
    return kg.provenance_chain(entity_type, canonical, max_depth=max_depth, max_visited=50)
```

**Test:**
```bash
python -m pytest tests/ -k "test_provenance" -x
```

### Task 5: Update Links.causal_chain semantics (0.5 day)

**Files:**
- `src/zettelforge/note_schema.py`

**Steps:**

1. Add docstring to `Links.causal_chain` clarifying it stores entity-level provenance references, not note-to-note links:

```python
class Links(BaseModel):
    """Conceptual links to other notes"""
    related: List[str] = Field(default_factory=list)
    superseded_by: Optional[str] = None
    supersedes: List[str] = Field(default_factory=list)
    causal_chain: List[str] = Field(
        default_factory=list,
        description="Entity-level causal provenance refs (entity_type:entity_value). "
                    "Use MemoryManager.provenance_chain() for full traversal.",
    )
```

### Task 6: Document enterprise divergence (0.25 day)

**Files:**
- `ARCHITECTURE.md` (create section or append)

Add section:

```markdown
## Knowledge Graph: Community vs Enterprise

### Edge Type Metadata
- **Community (JSONL):** Each edge carries an `edge_type` field: `"heuristic"`, `"causal"`, or `"temporal"`. Used by `GraphRetriever` to filter traversal.
- **Enterprise (TypeDB):** Edge types are implicit in `RELATION_MAP` relation names. No `edge_type` metadata field. Causal filtering uses TypeDB relation type queries.
```

## Commits

```
git add src/zettelforge/knowledge_graph.py src/zettelforge/graph_retriever.py \
  src/zettelforge/memory_manager.py src/zettelforge/note_constructor.py \
  src/zettelforge/note_schema.py ARCHITECTURE.md
```

1. `feat(kg): add edge_type field and causal edge filtering`
2. `feat(retriever): causal-only BFS traversal with 50-node cap`
3. `feat(recall): route CAUSAL intent to causal traversal`
4. `feat(kg): provenance_chain entity-to-entity causal trace`

## Risks

- **Fan-out cap too aggressive:** 50 nodes may be insufficient for deeply connected graphs. Monitor with structured logging and tune.
- **Backfill:** Existing edges have no `edge_type`. The `get("edge_type", "heuristic")` default handles this gracefully -- all legacy edges are treated as heuristic.
- **TypeDB divergence:** Enterprise users relying on causal traversal need a separate `TypeDBKnowledgeGraph.provenance_chain()` implementation. Track as follow-up.
