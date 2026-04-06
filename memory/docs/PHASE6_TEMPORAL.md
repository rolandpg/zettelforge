# Phase 6 Temporal Knowledge Graph — Port Summary

**Date:** 2026-04-05  
**Version:** 1.6.0  
**Status:** ✅ Complete

---

## Overview

Ported Phase 6 (The Knowledge Graph) from the A-MEM GitHub package with **temporal relationship extensions**. This enables explicit mapping of chronological relationships between events:

```
[Event A] → PRECEDES → [Event B]
[Event A] → CAUSES → [Event B]
[Event A] → ENABLES → [Event B]
```

---

## Files Added/Modified

### New Files

| File | Description | Lines |
|------|-------------|-------|
| `memory/temporal_knowledge_graph.py` | Core temporal graph implementation | 745 |
| `memory/temporal_graph_retriever.py` | Temporal query interface | 645 |
| `memory/__init__.py` | Module exports | 60 |
| `test_phase_6_temporal.py` | Comprehensive test suite (33 tests) | 740 |

### Modified Files

| File | Changes |
|------|---------|
| `memory/ontology_schema.json` | Added temporal relationship types and event entity type |

---

## Temporal Relationship Types

### Primary Relationships

| Type | Description | Direction |
|------|-------------|-----------|
| `PRECEDES` | Event A happens before Event B | A → B |
| `FOLLOWS` | Event A happens after Event B | A ← B |
| `CONCURRENT_WITH` | Events happen at roughly same time | A ↔ B |
| `IMMEDIATELY_PRECEDED_BY` | Event B immediately follows Event A | A ← B |
| `IMMEDIATELY_FOLLOWED_BY` | Event A immediately follows Event B | A → B |
| `OVERLAPS` | Event A time range overlaps Event B | A ↔ B |
| `CONTAINS` | Event A time range contains Event B | A → B |
| `CAUSES` | Event A causes Event B (temporal + causal) | A → B |
| `ENABLES` | Event A enables/preconditions Event B | A → B |
| `LEADS_TO` | Event A probabilistically leads to Event B | A → B |

### Inverse Relationships (auto-generated)

- `CONTAINED_BY`, `CAUSED_BY`, `ENABLED_BY`, `LED_FROM`

---

## Event Types (CTI-Focused)

Based on MITRE ATT&CK lifecycle:

- **Reconnaissance** (T1595-T1599)
- **Resource Development** (T1583-T1589)
- **Initial Access** (T1566-T1195)
- **Execution** (T1053-T1204)
- **Persistence** (T1098-T1547)
- **Privilege Escalation** (T1548-T1078)
- **Defense Evasion** (T1218-T1222)
- **Credential Access** (T1003-T1552)
- **Discovery** (T1087-T1120)
- **Lateral Movement** (T1021-T1210)
- **Collection** (T1005-T1125)
- **Command and Control** (T1071-T1219)
- **Exfiltration** (T1020-T1048)
- **Impact** (T1485-T1496)

Plus external events: CVE published, patch released, campaign start/end, etc.

---

## Core Capabilities

### 1. Event Management

```python
from memory import TemporalKnowledgeGraph, TemporalRelationship

tkg = TemporalKnowledgeGraph()

# Add event with timestamp
event = tkg.add_event(
    event_id="initial_access_001",
    event_type="initial_access",
    timestamp="2024-03-15T09:30:00Z",
    properties={"technique": "T1566.001", "actor": "apt28"}
)
```

### 2. Temporal Relationships

```python
# Create explicit temporal edge
tkg.add_temporal_edge(
    "event_a",
    "event_b", 
    TemporalRelationship.PRECEDES
)

# Auto-creates inverse edge (event_b FOLLOWS event_a)
```

### 3. Time-Based Queries

```python
# Get events in time range
events = tkg.get_events_between("2024-03-01", "2024-03-31")

# Get events before/after timestamp
before = tkg.get_events_before("2024-03-15T12:00:00Z")
after = tkg.get_events_after("2024-03-15T09:00:00Z")

# Get events on specific date
day_events = tkg.get_events_by_date("2024-03-15")
```

### 4. Event Chains

```python
# Get complete event chain
chain = tkg.get_event_chain("initial_access_001")

# Get preceding events
ancestors = tkg.get_preceding_events("impact_001", max_depth=5)

# Get following events
descendants = tkg.get_following_events("recon_001", max_depth=5)
```

### 5. Causal Analysis

```python
from memory import TemporalGraphRetriever

retriever = TemporalGraphRetriever()

# Find root causes
root_causes = retriever.find_root_causes("data_exfiltration_001")

# Get causal ancestors
ancestors = retriever.get_causal_ancestors("lateral_movement_001")

# Get causal descendants
descendants = retriever.get_causal_descendants("phishing_001")
```

### 6. Timeline Reconstruction

```python
# Reconstruct complete timeline
timeline = retriever.reconstruct_timeline(
    actor="apt28",
    time_range=("2024-03-01", "2024-03-31")
)

# Returns events, phases, patterns, metrics
```

### 7. Pattern Detection

```python
# Detect temporal patterns automatically
patterns = tkg.detect_temporal_patterns()

# Pattern types:
# - chain: A → B → C (sequential progression)
# - fan_out: A → B, A → C (single event → multiple)
# - fan_in: A → C, B → C (multiple → single)
```

### 8. Automatic Edge Inference

```python
# Automatically create PRECEDES edges based on timestamps
inferred_edges = tkg.infer_temporal_edges()
```

---

## Temporal Consistency Validation

The system enforces chronological consistency:

```python
# This will raise ValueError (temporal inconsistency)
tkg.add_temporal_edge(
    "event_at_10am",  # timestamp: 10:00
    "event_at_9am",   # timestamp: 09:00
    TemporalRelationship.PRECEDES  # Error: 10am cannot precede 9am
)
```

---

## Query Interface

Unified query interface for all temporal operations:

```python
# Query events in time range
result = retriever.query('events_between',
    start_time='2024-03-01',
    end_time='2024-03-31'
)

# Query event chain
result = retriever.query('event_chain',
    event_id='initial_access_001',
    max_length=10
)

# Query causal ancestors
result = retriever.query('causal_ancestors',
    event_id='impact_001',
    max_depth=5
)

# Query timeline
result = retriever.query('timeline',
    actor='apt28',
    time_range=('2024-03-01', '2024-03-31')
)
```

---

## Test Coverage

### Temporal Knowledge Graph Tests (20 tests)
- Event CRUD operations
- Temporal edge creation
- Consistency validation
- Chain traversal
- Time-based queries
- Pattern detection
- Persistence

### Temporal Graph Retriever Tests (10 tests)
- Time range queries
- Event chain retrieval
- Attack chain tracing
- Causal analysis
- Timeline reconstruction
- Query interface

### Integration Tests (3 tests)
- Full attack lifecycle
- Concurrent events
- Pattern detection (fan-out, fan-in)

**Total: 33 tests, all passing ✅**

---

## Storage

### Files Created

```
memory/
├── kg_nodes.jsonl          # Base graph nodes
├── kg_edges.jsonl          # Base graph edges
├── kg_policies.jsonl       # IEP policies
└── kg_temporal_edges.jsonl # Temporal relationships (new)
```

All storage is append-only JSONL for durability and auditability.

---

## Integration with Existing A-MEM

The temporal knowledge graph integrates seamlessly with existing A-MEM components:

```
Primary Agent
     │
     ├─→ MemoryManager (existing)
     │    ├─→ MemoryStore (existing)
     │    ├─→ EntityIndexer (existing)
     │    └─→ ...
     │
     ├─→ KnowledgeGraph (Phase 6)
     │    └─→ TemporalKnowledgeGraph (Phase 6 Extension)
     │         ├─→ TemporalGraphRetriever
     │         └─→ kg_temporal_edges.jsonl
     │
     └─→ GraphRetriever (Phase 6)
          └─→ TemporalGraphRetriever
```

---

## Usage Example: Attack Timeline Analysis

```python
from memory import (
    TemporalKnowledgeGraph,
    TemporalGraphRetriever,
    TemporalRelationship
)

# Initialize
tkg = TemporalKnowledgeGraph()
retriever = TemporalGraphRetriever()

# Log attack events
events = [
    ("recon", "2024-03-15T08:00:00Z", "T1595"),
    ("phishing", "2024-03-15T09:30:00Z", "T1566.001"),
    ("exec", "2024-03-15T09:32:00Z", "T1059.001"),
    ("persist", "2024-03-15T09:45:00Z", "T1547.001"),
    ("c2", "2024-03-15T11:00:00Z", "T1071.001"),
    ("exfil", "2024-03-15T14:00:00Z", "T1041"),
]

for i, (eid, ts, tech) in enumerate(events):
    tkg.add_event(eid, "custom", ts, {"technique": tech})
    if i > 0:
        tkg.add_temporal_edge(events[i-1][0], eid, TemporalRelationship.PRECEDES)

# Analyze
timeline = retriever.reconstruct_timeline()
print(f"Attack duration: {timeline['metrics']['time_span_minutes']} minutes")
print(f"Techniques used: {timeline['metrics']['unique_techniques']}")

# Find root cause
root_causes = retriever.find_root_causes("exfil")
print(f"Root cause: {root_causes[0]['event']['properties']['event_id']}")
```

---

## References

- A-MEM Paper: [arXiv:2502.12110](https://arxiv.org/abs/2502.12110)
- A-MEM Repository: https://github.com/agiresearch/A-mem
- MITRE ATT&CK: https://attack.mitre.org/

---

## Next Steps

1. **Phase 6 + 7 Integration**: Connect temporal queries with synthesis layer
2. **Visualization**: Export timelines to Mermaid/Graphviz
3. **Pattern Learning**: ML-based detection of attack patterns
4. **Alerting**: Temporal rule engine for real-time detection

---

*End of Phase 6 Temporal Port Summary*
