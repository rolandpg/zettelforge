# Memory System Improvement Plan
**Status:** Active — Version 1.1
**Created:** 2026-03-31
**Updated:** 2026-03-31 (Phase 2 complete)
**Owner:** Patton (Roland Fleet Memory System)
**Review cadence:** Weekly via cron — `0 11 * * 1` (Mondays 6 AM CDT)

---

## The Problem

The memory system had no entity indexing and no deduplication. This caused:
1. Near-duplicate notes from repeated observations of the same entity
2. No fast lookup by known entity (CVE-ID, actor name, tool)
3. No supersedes tracking when decisions change over time
4. Manual linking that should have been automatic

---

## Improvement Roadmap

### Phase 1: Entity Indexing ✅ — Done 2026-03-31
**Goal:** Enable instant lookup by known entity type without semantic search.

**Components built:**
- `entity_indexer.py` — EntityExtractor + EntityIndexer + Deduplicator
  - Extracts: CVE-IDs, threat actors, tools, campaigns, sectors
  - Pattern matching on 50+ actors, 30+ tools, sector keywords
  - Persistent `entity_index.json` mapping entity → note IDs
- `memory_manager.py` fully integrated:
  - `mm.recall_cve()`, `mm.recall_actor()`, `mm.recall_tool()`, `mm.recall_campaign()`
  - `mm.remember()` now deduplicates by CVE before saving
  - `mm.get_entity_stats()`, `mm.rebuild_entity_index()`
  - Daily maintenance rebuilds entity index
- **Verified:** recall_cve(CVE-2024-3094) → 5 notes instantly; duplicate CVE → skipped

**Result:** 24 entities indexed across 40 notes. Instant typed lookup replacing semantic search.

---

### Phase 2: Working Link Generator Integration ✅ — Done 2026-03-31
**Goal:** Automatic concept links at save time, entity-guided candidate retrieval.

**What was built:**
- `_get_entity_correlated_notes()` in link_generator.py: pulls notes sharing same CVE/actor/tool/campaign even if not yet linked — uses entity_index.json
- `_get_entity_related_notes()` in memory_evolver.py: same logic for evolution assessment
- `generate_links()`: prioritizes entity-matched candidates for LLM prompt
- `run_evolution_cycle()`: now also assesses entity-correlated notes even if not yet linked

**Result:** New MuddyWater note linked to 9 related notes (Volt Typhoon/CISA advisory cluster) via entity correlation. Previously: only semantic similarity candidates.

---

### Phase 3: Date-Aware Retrieval ⚪ (Future)
**Goal:** Newer notes automatically supersede older conflicting notes in retrieval.

**Mechanism:**
- Add `supersedes: List[str]` field to note metadata
- When retrieving, filter out notes superseded by a more recent note on the same entity
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

## Current State (v1.1)

| Component | Status |
|---|---|
| Entity extraction | ✅ 24 entities (3 CVEs, 9 actors, 3 tools, 9 sectors) |
| Entity index | ✅ entity_index.json persistent |
| Fast lookup | ✅ mm.recall_cve/actor/tool/campaign() |
| Deduplication | ✅ CVE deduplication before save |
| Entity-guided linking | ✅ Phase 2 complete |
| Evolution → entity notes | ✅ Phase 2 complete |
| Date-aware retrieval | ⚪ Future |
| Mid-session refresh | ⚪ Future |
| Cold archive | ⚪ Future |

---

## Iteration Log

| Date | Iter | Phase | Entities | Notes | Dups Skipped | Action |
|---|---|---|---|---|---|---|
| 2026-03-31 | v1.0 | Phase 1 | 22 | 37 | — | Plan created, entity_indexer.py built |
| 2026-03-31 | v1.1 | Phase 2 | 24 | 42 | 2 | Link generator + evolution use entity index |
