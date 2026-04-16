# Implementation Plan: Persistence Semantics (Feature 5)

**Date:** 2026-04-15
**Estimated effort:** 2-3 days
**Branch:** `feat/persistence-semantics`

## Goal

Add a `persistence_semantics` field to notes with four values: `knowledge`, `memory`, `wisdom`, `intelligence`. Each tier has different TTL behavior and update rules. Fix the adversarial review findings on TTL silent drops, circular wisdom gates, unmapped source types, and backfill.

## Architecture Decisions

### AD-1: Persistence tier definitions

| Tier | Description | TTL | Decay | Update Rule |
|------|-------------|-----|-------|-------------|
| `knowledge` | Authoritative facts (CVEs, STIX objects) | None (permanent) | None | Overwrite on newer source |
| `memory` | Operational observations, conversations | 90 days (access resets) | Confidence -0.01/week inactive | Standard supersession |
| `wisdom` | Cross-referenced insights | None (permanent) | None | Requires new_note + 1 existing note_id in evidence |
| `intelligence` | Synthesized assessments | 180 days | Confidence -0.005/week | Versioned (keep history) |

### AD-2: Wisdom gate (fixes WARNING-13)

The original design required 2 entries in `evolved_by`, but wisdom notes start empty. Fix: wisdom creation requires `new_note` (the new content) plus at least 1 existing `note_id` in an `evidence` list. This is checked at creation time, not retroactively.

```python
def validate_wisdom_creation(note: MemoryNote, evidence_note_ids: List[str]) -> bool:
    """Wisdom notes require at least 1 existing note as evidence."""
    return len(evidence_note_ids) >= 1
```

### AD-3: Source type mapping (fixes WARNING-14)

All `source_type` values get explicit mapping. Unknown types default to `"memory"`.

```python
SOURCE_TYPE_TO_PERSISTENCE = {
    "conversation": "memory",
    "task_output": "memory",
    "ingestion": "knowledge",
    "observation": "memory",
    "report": "knowledge",       # Was unmapped
    "mcp": "knowledge",          # Was unmapped
    "opencti_sync": "knowledge",
    "synthesis": "intelligence",
    "evolution": "intelligence",
}

def infer_persistence(source_type: str) -> str:
    return SOURCE_TYPE_TO_PERSISTENCE.get(source_type, "memory")
```

### AD-4: TTL filtering in recall() (fixes WARNING-12)

`recall()` gets an `include_expired: bool = False` parameter. When `False`, expired notes are filtered out. Response metadata includes `filtered_expired_count` so callers know results were dropped.

### AD-5: Backfill strategy (fixes WARNING-15)

Existing notes get `persistence_semantics="memory"` with `ttl_anchor` set to the migration timestamp, not `created_at`. This prevents old notes from immediately expiring.

### AD-6: TTL naming (fixes NIT-3)

Do not call the TTL "Ebbinghaus-style". It is a simple TTL with access-based reset. Documentation and code comments will say "access-reset TTL".

## Tasks

### Task 1: Extend Metadata with persistence fields (0.5 day)

**Files:**
- `src/zettelforge/note_schema.py`

**Steps:**

1. Add fields to `Metadata`:

```python
class Metadata(BaseModel):
    """Note lifecycle and access metadata"""
    access_count: int = 0
    last_accessed: Optional[str] = None
    evolution_count: int = 0
    confidence: float = 1.0
    ttl: Optional[int] = None  # Access-reset TTL in days (not Ebbinghaus)
    ttl_anchor: Optional[str] = None  # ISO timestamp: TTL counts from this date
    persistence_semantics: str = "memory"  # knowledge | memory | wisdom | intelligence
    domain: str = "general"
    tier: str = "B"
    importance: int = 5
    tlp: str = ""
    stix_confidence: int = -1
    vuln: Optional[VulnerabilityMeta] = None
```

2. Add `is_expired()` method to `MemoryNote`:

```python
def is_expired(self) -> bool:
    """Check if note has exceeded its access-reset TTL."""
    if self.metadata.ttl is None:
        return False
    from datetime import datetime, timedelta

    # Use last_accessed if available, else ttl_anchor, else created_at
    anchor = (
        self.metadata.last_accessed
        or self.metadata.ttl_anchor
        or self.created_at
    )
    try:
        anchor_dt = datetime.fromisoformat(anchor)
        return datetime.now() > anchor_dt + timedelta(days=self.metadata.ttl)
    except (ValueError, TypeError):
        return False
```

**Test:**
```bash
python -m pytest tests/ -k "test_note_schema" -x
```

### Task 2: Persistence inference module (0.5 day)

**Files:**
- `src/zettelforge/persistence.py` (new file)

**Steps:**

1. Create module with source type mapping and TTL defaults:

```python
"""
Persistence Semantics — tier assignment and TTL rules.

Four tiers: knowledge (permanent), memory (90d TTL), wisdom (permanent, gated),
intelligence (180d TTL). TTL uses access-reset: accessing a note resets its
expiry clock.
"""

from typing import Dict, List, Optional

from zettelforge.log import get_logger
from zettelforge.note_schema import MemoryNote

_logger = get_logger("zettelforge.persistence")

# Source type -> persistence tier
SOURCE_TYPE_TO_PERSISTENCE: Dict[str, str] = {
    "conversation": "memory",
    "task_output": "memory",
    "ingestion": "knowledge",
    "observation": "memory",
    "report": "knowledge",
    "mcp": "knowledge",
    "opencti_sync": "knowledge",
    "synthesis": "intelligence",
    "evolution": "intelligence",
}

# TTL defaults per tier (days, None = permanent)
TIER_TTL: Dict[str, Optional[int]] = {
    "knowledge": None,
    "memory": 90,
    "wisdom": None,
    "intelligence": 180,
}

# Confidence decay per week of inactivity
TIER_DECAY: Dict[str, float] = {
    "knowledge": 0.0,
    "memory": 0.01,
    "wisdom": 0.0,
    "intelligence": 0.005,
}


def infer_persistence(source_type: str) -> str:
    """Map source_type to persistence tier. Defaults to 'memory'."""
    return SOURCE_TYPE_TO_PERSISTENCE.get(source_type, "memory")


def apply_persistence_defaults(note: MemoryNote) -> MemoryNote:
    """Set TTL and persistence_semantics based on source_type if not already set."""
    if note.metadata.persistence_semantics == "memory" and note.metadata.ttl is None:
        tier = infer_persistence(note.content.source_type)
        note.metadata.persistence_semantics = tier
        note.metadata.ttl = TIER_TTL.get(tier)
    return note


def validate_wisdom_creation(
    note: MemoryNote, evidence_note_ids: List[str]
) -> bool:
    """
    Wisdom notes require at least 1 existing note as evidence.
    Prevents circular gate where wisdom can never be created.
    """
    return len(evidence_note_ids) >= 1


def filter_expired(
    notes: List[MemoryNote], include_expired: bool = False
) -> tuple:
    """
    Filter expired notes from results.

    Returns:
        (filtered_notes, expired_count)
    """
    if include_expired:
        return notes, 0

    active = []
    expired_count = 0
    for note in notes:
        if note.is_expired():
            expired_count += 1
        else:
            active.append(note)
    return active, expired_count
```

**Test:**
```bash
python -m pytest tests/ -k "test_persistence" -x
```

### Task 3: Wire persistence into remember() and recall() (1 day)

**Files:**
- `src/zettelforge/memory_manager.py`

**Steps:**

1. In `remember()`, after constructing the note, apply persistence defaults:

```python
from zettelforge.persistence import apply_persistence_defaults

# After: note = self.constructor.construct(...)
note = apply_persistence_defaults(note)
```

2. In `recall()`, add `include_expired` parameter and filter:

```python
def recall(
    self,
    query: str,
    domain: Optional[str] = None,
    k: int = 10,
    include_links: bool = True,
    exclude_superseded: bool = True,
    include_expired: bool = False,  # NEW
) -> List[MemoryNote]:
    # ... existing retrieval logic ...

    # After supersession filter, before cap at k:
    from zettelforge.persistence import filter_expired
    results, expired_count = filter_expired(results, include_expired)

    if expired_count > 0:
        self._logger.info(
            "recall_expired_filtered",
            query=query[:100],
            expired_count=expired_count,
        )

    # Cap at k
    results = results[:k]
    # ... rest of method ...
```

3. In `remember()`, set `ttl_anchor` to now for new notes:

```python
from datetime import datetime
note.metadata.ttl_anchor = datetime.now().isoformat()
```

4. In `increment_access()` on `MemoryNote`, the existing `last_accessed` update already resets the TTL clock (the `is_expired()` method checks `last_accessed` first).

**Test:**
```bash
python -m pytest tests/ -k "test_recall" -x
python -m pytest tests/ -k "test_remember" -x
```

### Task 4: Backfill migration script (0.5 day)

**Files:**
- `scripts/backfill_persistence.py` (new file)

**Steps:**

1. Create migration script that reads all notes from JSONL, adds `persistence_semantics="memory"` and `ttl_anchor=<migration_timestamp>` to notes that lack these fields:

```python
"""
Backfill persistence_semantics for existing notes.

Sets all notes without persistence_semantics to "memory" with
ttl_anchor = migration timestamp (NOT created_at, to prevent
immediate expiry of old notes).
"""

import sys
from datetime import datetime
from zettelforge.memory_store import MemoryStore

def backfill():
    migration_ts = datetime.now().isoformat()
    store = MemoryStore()
    updated = 0

    for note in store.iterate_notes():
        changed = False

        if not hasattr(note.metadata, "persistence_semantics") or \
           note.metadata.persistence_semantics == "memory" and note.metadata.ttl is None:
            from zettelforge.persistence import infer_persistence, TIER_TTL
            tier = infer_persistence(note.content.source_type)
            note.metadata.persistence_semantics = tier
            note.metadata.ttl = TIER_TTL.get(tier)
            note.metadata.ttl_anchor = migration_ts  # NOT created_at
            changed = True

        if changed:
            store._rewrite_note(note)
            updated += 1

    print(f"Backfilled {updated} notes with persistence_semantics (anchor: {migration_ts})")

if __name__ == "__main__":
    backfill()
```

**Test:**
```bash
python scripts/backfill_persistence.py
python -m pytest tests/ -k "test_persistence" -x
```

### Task 5: Tests (0.5 day)

**Files:**
- `tests/test_persistence.py` (new)

**Steps:**

1. Test `infer_persistence()` for all mapped source types + unknown defaults to "memory".
2. Test `is_expired()` with:
   - No TTL (permanent) -> False
   - TTL set, recently accessed -> False
   - TTL set, expired -> True
   - TTL set, no access, ttl_anchor within window -> False
3. Test `validate_wisdom_creation()` with 0 evidence (fail) and 1+ evidence (pass).
4. Test `filter_expired()` returns correct counts.
5. Test `recall(include_expired=True)` returns expired notes.
6. Test backfill sets `ttl_anchor` to migration timestamp, not `created_at`.

## Commits

1. `feat(schema): add persistence_semantics, ttl_anchor to Metadata`
2. `feat(persistence): tier inference, TTL rules, wisdom gate`
3. `feat(recall): add include_expired filter with expired count logging`
4. `feat(backfill): migration script for existing notes`

## Risks

- **TTL too aggressive for memory tier:** 90 days may be too short for infrequently-accessed but valuable operational notes. Configurable per-domain in a future pass.
- **Wisdom gate still manual:** Creation of wisdom notes requires explicit `evidence_note_ids`. No automatic promotion path exists yet. Track as follow-up.
- **Backfill idempotency:** Running the backfill script twice should be safe (it checks for existing values), but should log "already backfilled" counts for auditability.
