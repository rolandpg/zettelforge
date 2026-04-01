# Memory System Improvement Plan
**Status:** Active — Version 1.0
**Created:** 2026-03-31
**Owner:** Patton (Roland Fleet Memory System)
**Review cadence:** Weekly via cron

---

## The Problem

The memory system has no entity indexing and no deduplication. This causes:
1. Near-duplicate notes created from repeated observations of the same entity
2. No fast lookup by known entity (CVE-ID, actor name, tool)
3. No supersedes tracking when decisions change over time
4. Manual linking that should be automatic

---

## Improvement Roadmap

### Phase 1: Entity Indexing ✅ (This Session)
**Goal:** Enable instant lookup by known entity type without semantic search.

**Components:**
- `entity_indexer.py` — extracts entities from note content (CVE-IDs, threat actors, tools, sectors, campaigns)
- `entity_index.json` — persistent secondary index mapping entity → note IDs
- `mm.recall_entity(entity_type, entity_value)` — fast lookup
- `mm.recall_cve(cve_id)`, `mm.recall_actor(actor_name)` — typed lookups

**Entities to track:**
| Entity Type | Examples | Detection Pattern |
|---|---|---|
| CVE-ID | CVE-2024-3094, CVE-2026-3055 | `CVE-\d{4}-\d{4,}` |
| Threat Actor | Volt Typhoon, MuddyWater, APT29 | Named entity extraction |
| Tool/Campaign | Havoc, Cobalt Strike, TrueChaos | Named entity extraction |
| Sector | DIB, MSSP, Healthcare | Domain keyword match |
| Campaign | Operation NoVoice, Operation DualScript | Named extraction |

**Deduplication rules:**
- Before saving: check if note about same CVE-ID exists → skip duplicate
- Before saving: compute content similarity vs. recent 50 notes → if >0.85 similarity, warn or skip
- When skipping: log to deduplication log with reason

**Supersedes tracking:**
- `note.links.superseded_by` field already exists in schema — use it
- When a newer note contradicts an older one (same CVE, different conclusion), mark old as superseded

**Status:** Built, needs integration into memory_manager.py save flow

---

### Phase 2: Working Link Generator Integration 🔧 (Next Session)
**Goal:** Automatic concept links created at save time, not as a separate step.

**Current state:** `link_generator.py` exists but isn't called during `mm.remember()`. The code in `memory_manager.py` calls it but only against in-memory candidates — not against the full note store efficiently.

**What works:**
- `NoteConstructor` — enriches with semantic context, keywords, tags, entities
- `LinkGenerator` — SUPPORTS / CONTRADICTS / EXTENDS / CAUSES / RELATED
- `MemoryEvolver` — confidence decay, flagging

**What's broken:**
- Link generation only runs against notes in memory, not the full JSONL store efficiently
- Evolution runs but results aren't persisted back correctly

**Fix:**
- Batch link generation for new notes against top-k similar notes (not full scan)
- Ensure evolution results write back to JSONL

---

### Phase 3: Date-Aware Retrieval ⚪ (Future)
**Goal:** Newer notes automatically supersede older conflicting notes in retrieval.

**Mechanism:**
- Add `supersedes: List[str]` field to note metadata
- When retrieving, filter out notes that are superseded by a more recent note on the same entity
- Sort by date, prefer recent

---

### Phase 4: Mid-Session Snapshot Refresh ⚪ (Future)
**Goal:** Frozen snapshot updates mid-session when memory files change.

**Mechanism:**
- Before any `mm.remember()` call, snapshot is fresh
- After, invalidate and refresh from JSONL on next `mm.recall()`
- Or: write-through — `remember()` updates both JSONL and snapshot

---

### Phase 5: Cross-Session Forgetting ⚪ (Future)
**Goal:** Low-confidence, unaccessed notes archived to cold storage automatically.

**Mechanism:**
- Notes with confidence < 0.3 and access_count == 0 for > 30 days → archive
- Archive = move to cold_path + remove from active JSONL
- Can be restored on query

---

## Current Entity Index State

**Index path:** `memory/entity_index.json`
**Last rebuilt:** Not yet built (Phase 1 pending integration)
**Entities tracked:** 0 (index empty)

## Deduplication Log

**Path:** `memory/dedup_log.jsonl`
**Last entry:** None

---

## Improvement Iterations (Cron Log)

| Date | Iter | Actions | Notes |
|---|---|---|---|
| 2026-03-31 | v1.0 | Plan created, entity_indexer.py drafted | Phase 1 in progress |
