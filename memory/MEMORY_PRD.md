# Memory System PRD — Roland Fleet Agentic Memory
**Version:** 1.0
**Date:** 2026-03-31
**Owner:** Patton (Roland Fleet Memory System)
**Status:** Phases 1-2 Complete | Phase 3-5 Pending

---

## 1. Problem Statement

The Roland Fleet memory system suffers from four chronic failures:

1. **No entity indexing** — Agents cannot retrieve information by known entity type. A query for "Volt Typhoon" requires semantic similarity search that may miss notes simply because the phrasing differs.

2. **No deduplication** — The same CVE, actor, or finding recorded from different sessions produces near-identical notes that accumulate silently.

3. **Brittle linking** — The link generator operates on whatever candidates are loaded in memory, missing related notes that aren't yet connected. The memory graph never closes.

4. **No memory hygiene** — Low-confidence, unaccessed notes accumulate in the active store indefinitely. The system grows dense with stale information.

---

## 2. Product Vision

A self-organizing memory system that compounds over time — where every note automatically discovers its relationship to existing knowledge, stale knowledge is archived, and agents can retrieve information by entity type without search.

**Core principle:** The system should require zero manual organization. An agent reading a note about MuddyWater should have zero friction finding the MuddyWater note — not "search for MuddyWater and hope the semantic similarity picks it up."

---

## 3. Scope

### In Scope
- Entity extraction from note content (CVE-IDs, threat actors, tools, campaigns, sectors)
- Persistent entity index (entity → note ID mapping)
- Fast typed retrieval: `mm.recall_cve()`, `mm.recall_actor()`, `mm.recall_tool()`, `mm.recall_campaign()`
- Deduplication: same CVE saved twice → skip, log, return existing
- Entity-guided link generation: new notes automatically link to related notes sharing entities
- Entity-guided evolution: new notes trigger assessment of entity-related notes even if unlinked
- Weekly plan reviewer: automated iteration and health reporting
- Cold archival of low-confidence, unaccessed notes

### Out of Scope
- Cross-device sync (single machine homelab)
- GUI or visualization (text-only, API-first)
- Non-cybersecurity domains beyond what the agent captures

---

## 4. User Stories

### Story 1: Entity Recall
**As** an agent,
**I want** to retrieve all notes about a specific CVE or actor instantly,
**So** I don't miss context that semantic search might not surface.

**Acceptance:** `mm.recall_cve('CVE-2024-3094')` returns all notes referencing that CVE within 100ms, without semantic query.

### Story 2: Duplicate Prevention
**As** an agent,
**I want** the system to skip saving a note that duplicates an existing CVE note,
**So** the knowledge base doesn't bloat with redundant entries.

**Acceptance:** Calling `mm.remember()` with content about an already-indexed CVE returns `(existing_note, 'duplicate_skipped:reason')` — no new note created.

### Story 3: Automatic Graph Closure
**As** an agent,
**I want** new notes to automatically link to all existing notes sharing entities,
**So** the memory graph closes without manual organization.

**Acceptance:** A new note about MuddyWater links to Volt Typhoon notes (same actor family), CISA advisory notes, and any existing MuddyWater notes — without the agent explicitly searching for them first.

### Story 4: Evolution Beyond Links
**As** an agent,
**I want** new information about an entity to trigger evolution of existing notes about that entity,
**So** the knowledge base reflects the latest understanding.

**Acceptance:** A new note with updated intelligence about Volt Typhoon triggers assessment of all existing Volt Typhoon notes — even those not yet linked to the new note.

### Story 5: System Health Reporting
**As** the operator,
**I want** an automated weekly review of memory system health,
**So** I know which phases need attention and what the system learned.

**Acceptance:** `memory_plan_reviewer.py` runs on cron, logs iteration to `plan_iterations.jsonl`, and identifies the next priority action.

---

## 5. Technical Architecture

### 5.1 Entity Index
**File:** `memory/entity_index.json`
**Structure:**
```json
{
  "cve":   { "cve-2024-3094": ["note_id_1", "note_id_2"] },
  "actor": { "volt typhoon":  ["note_id_3"] },
  "tool":  { "cobalt strike": ["note_id_4"] },
  ...
}
```

**Indexing:** Entity extraction runs on every `mm.remember()` call. Index is updated immediately after note creation. Daily maintenance rebuilds from scratch.

**Extractor patterns:**
- CVE: `CVE-\d{4}-\d{4,}` (case-insensitive)
- Actor: Named entity list (~50 actors) + heuristic extraction
- Tool: Named tool list (~30 tools) + heuristic
- Campaign: `Operation\s+\w+` pattern
- Sector: Keyword matching (DIB, Healthcare, MSSP, OT, etc.)

### 5.2 Memory Note Lifecycle
```
mm.remember(content)
  │
  ├─► Deduplication check
  │     ├─► Same CVE → (existing_note, "duplicate_skipped") ← EXIT
  │     └─► Similar > 0.85 → log, continue to save
  │
  ├─► Note construction (semantic enrichment via LLM)
  │
  ├─► Store write (append to notes.jsonl)
  │
  ├─► Entity index update (entity_index.json)
  │
  ├─► Entity-guided link generation
  │     ├─► Pull candidates from entity index
  │     ├─► Prioritize entity-matched over semantic-only
  │     └─► LLM classify: SUPPORTS/CONTRADICTS/EXTENDS/CAUSES/RELATED
  │
  ├─► Entity-guided evolution cycle
  │     ├─► Find entity-correlated notes (not just linked)
  │     ├─► Assess each: NO_CHANGE / UPDATE_CONTEXT / UPDATE_TAGS / UPDATE_BOTH / SUPERSEDE
  │     └─► Archive evolved notes to cold storage
  │
  └─► Return (note, reason)
```

### 5.3 Cold Storage
**Archive path:** `/media/rolandpg/USB-HDD/archive/`
**Format:** `note_id_v{version}.jsonl`
**Trigger:** On evolution, old version is archived before update is written

---

## 6. Phase Definitions

### Phase 1: Entity Indexing ✅
| Requirement | Test |
|---|---|
| Entity extraction from note content | `extract_all()` returns correct entities for known CVE, actor, tool, campaign, sector text |
| Entity index persisted to disk | `entity_index.json` exists and maps entities to note IDs |
| Index rebuilt from notes.jsonl | `rebuild_entity_index()` produces correct mappings |
| `mm.recall_cve()` works | Returns notes referencing that CVE |
| `mm.recall_actor()` works | Returns notes referencing that actor |
| `mm.recall_tool()` works | Returns notes referencing that tool |
| `mm.recall_campaign()` works | Returns notes referencing that campaign |
| `mm.recall_entity()` typed lookup works | Returns notes for given type+value |
| `mm.get_entity_stats()` works | Returns breakdown by entity type |

### Phase 2: Entity-Guided Linking ✅
| Requirement | Test |
|---|---|
| Link generator uses entity index for candidates | New note about actor links to existing actor notes |
| Prioritized candidates include entity matches | Entity-matched notes appear in LLM prompt before semantic-only |
| New note links to same-CVE notes | A new CVE note links to existing notes about same CVE |
| New note links to same-actor notes | A new actor note links to existing notes about same actor |
| Evolution assesses entity-correlated notes | Evolution cycle finds notes sharing entities even if not linked |
| `_get_entity_related_notes()` returns correct notes | Returns notes with matching CVE/actor/tool/campaign |

### Phase 3: Date-Aware Retrieval ⚪
| Requirement | Test |
|---|---|
| Supersedes tracking | Newer note on same entity marks older as superseded |
| Retrieval excludes superseded notes | `recall()` filters out notes superseded by a more recent note |
| Supersedes metadata persisted | Supersedes relationship survives JSONL write/read cycle |

### Phase 4: Mid-Session Snapshot Refresh ⚪
| Requirement | Test |
|---|---|
| Snapshot reflects recent saves | Calling `get_snapshot()` after `remember()` returns updated notes |
| Fresh snapshot on recall | `recall()` after `remember()` in same session finds new notes |

### Phase 5: Cold Archive ⚪
| Requirement | Test |
|---|---|
| Low-confidence notes archived | Notes with confidence < 0.3 and access_count == 0 for > 30 days archived |
| Archived notes excluded from active recall | `recall()` does not return archived notes |
| Archive directory created | `/media/rolandpg/USB-HDD/archive/` created on archive operation |

---

## 7. Success Metrics

| Metric | Target |
|---|---|
| Entity index coverage | > 80% of notes have at least one entity extracted |
| Duplicate skip rate | > 10% of saves are duplicates (indicating dedup working) |
| Average links per note | > 2 (indicating graph is closing) |
| Entity-guided link ratio | > 50% of links come from entity-correlated candidates (not pure semantic) |
| Cold archive size | Growing as low-confidence notes are archived |
| Plan reviewer iterations | At least 1 per week logged |

---

## 8. Testability

Every phase must be verifiable by an automated test that:
- Runs in isolation without external services
- Fails with a specific phase/requirement indicator
- Reports which component failed and why
- Can be run by `python3 memory/test_memory_system.py`

---

## 9. Open Questions

1. Should similarity threshold for duplicate detection be tunable per domain?
2. Should archived notes be queryable via a special `mm.recall_archived()` method?
3. Should the plan reviewer have authority to automatically promote Phase X to "in progress" or only report?
