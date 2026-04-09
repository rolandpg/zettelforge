---
title: "Run Temporal Queries"
description: "Query temporal relationships including entity timelines, change tracking, and valid-from/valid-until ranges using the temporal graph index."
diataxis_type: "how-to"
audience: "CTI analysts tracking threat actor evolution, security teams monitoring intelligence changes"
tags: [temporal, timeline, knowledge-graph, changes-since, cti]
last_updated: "2026-04-09"
version: "2.0.0"
---

# Run Temporal Queries

Query how entities change over time using ZettelForge's temporal graph index. Track entity timelines, detect superseded intelligence, and retrieve all changes since a given timestamp.

## Prerequisites

- ZettelForge with stored CTI data
- Embedding and LLM models available (download automatically on first use)

## Steps

### 1. Store notes at different times to create temporal data

```python
from zettelforge.memory_manager import MemoryManager

mm = MemoryManager()

# Store initial intelligence
note1, _ = mm.remember(
    content="APT28 used Cobalt Strike for C2 in January 2026 campaigns targeting EU governments.",
    source_type="report",
    source_ref="vendor-report-jan-2026",
    domain="cti"
)

# Store updated intelligence (later observation)
note2, _ = mm.remember(
    content="APT28 shifted to Sliver C2 framework in March 2026, replacing Cobalt Strike in EU operations.",
    source_type="report",
    source_ref="vendor-report-mar-2026",
    domain="cti"
)
```

> [!NOTE]
> When `note2` shares overlapping entities with `note1`, ZettelForge automatically evaluates supersession. If the overlap score exceeds the threshold, the older note is marked `superseded_by` the newer one, and a `SUPERSEDES` temporal edge is added to the graph.

### 2. Get an entity's timeline

```python
from zettelforge.knowledge_graph import get_knowledge_graph

kg = get_knowledge_graph()

timeline = kg.get_entity_timeline(
    entity_type="actor",
    entity_value="apt28"
)

for entry in timeline:
    print(f"  [{entry['timestamp']}] "
          f"{entry['edge']['relationship']} -> "
          f"{entry['to_entity']}")
```

Expected output:

```
  [2026-04-09T10:00:00] SUPERSEDES -> note:<note1_id>
  [2026-04-09T10:01:00] MENTIONED_IN -> note:<note2_id>
```

### 3. Get all changes since a timestamp

```python
changes = kg.get_changes_since("2026-03-01T00:00:00")

for change in changes:
    print(f"  [{change['timestamp']}] "
          f"{change['from']} --{change['relationship']}--> "
          f"{change['to']}")
```

### 4. Query with temporal intent via `recall()`

```python
notes = mm.recall(
    query="How has APT28 tooling changed since January 2026?",
    domain="cti",
    k=10
)

for note in notes:
    superseded = "SUPERSEDED" if note.links.superseded_by else "CURRENT"
    print(f"  [{superseded}] {note.created_at[:10]}: {note.content.raw[:80]}")
```

> [!TIP]
> By default, `recall()` filters out superseded notes (`exclude_superseded=True`). Pass `exclude_superseded=False` to include historical versions for timeline reconstruction.

### 5. Synthesize a timeline analysis

```python
result = mm.synthesize(
    query="Timeline of APT28 tool changes in 2026",
    format="timeline_analysis",
    k=10
)

print(result["synthesis"]["summary"])
```

### 6. Check supersession status of a specific note

```python
note = mm.store.get_note_by_id(note1.id)

if note.links.superseded_by:
    print(f"Note {note.id} was superseded by {note.links.superseded_by}")
    newer = mm.store.get_note_by_id(note.links.superseded_by)
    print(f"  Newer content: {newer.content.raw[:100]}")
else:
    print(f"Note {note.id} is current (not superseded)")
```

### 7. Ingest reports with published dates for temporal context

```python
results = mm.remember_report(
    content="Lazarus Group deployed new DTrack variant in February 2026...",
    source_url="https://example.com/lazarus-feb-2026",
    published_date="2026-02-15",
    domain="cti"
)
```

The `published_date` is passed as context to the extraction LLM, enabling it to anchor facts temporally.

> [!WARNING]
> The temporal index uses ISO 8601 string comparison for ordering. Always use full ISO timestamps (`2026-03-01T00:00:00`) rather than partial dates (`2026-03-01`) for consistent `get_changes_since()` results.

## LLM Quick Reference

**Task**: Query how threat intelligence entities change over time using temporal graph features.

**Entity timeline**: `kg.get_entity_timeline(entity_type, entity_value)` returns `List[Dict]` sorted by timestamp. Each entry has `edge`, `timestamp`, `to_entity` fields.

**Changes since**: `kg.get_changes_since(timestamp_iso)` returns `List[Dict]` of all temporal edges (TEMPORAL_BEFORE, TEMPORAL_AFTER, SUPERSEDES) after the given timestamp. Fields: `timestamp`, `from`, `relationship`, `to`.

**Supersession**: When a new note overlaps entities with an existing note and scores above threshold, ZettelForge marks the old note's `links.superseded_by` and adds a `SUPERSEDES` edge to the graph.

**Recall filtering**: `mm.recall(query, exclude_superseded=True)` (default) hides outdated notes. Set `False` for historical analysis.

**Temporal synthesis**: `mm.synthesize(query, format="timeline_analysis")` produces chronological reconstruction from retrieved notes.

**Published date**: `mm.remember_report(content, published_date="2026-02-15")` anchors extracted facts to a publication date for temporal ordering.

**Temporal edge types**: `TEMPORAL_BEFORE`, `TEMPORAL_AFTER`, `SUPERSEDES`. All stored in the knowledge graph's temporal index and queryable via `get_changes_since()`.
