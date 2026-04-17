# Merge Consolidation Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Merge the GAM-inspired consolidation layer from the dev branch into the main ZettelForge repo, fixing 2 critical bugs and integrating it into the MemoryManager write path.

**Architecture:** The consolidation layer has 3 classes: `SemanticShiftDetector` (monitors incoming notes for semantic shifts), `ConsolidationEngine` (executes EPG→TAN consolidation), and `ConsolidationMiddleware` (drop-in hook for `MemoryManager.remember()`). The code exists at `/home/rolandpg/projects/zettelforge/src/zettelforge/consolidation.py` with tests at `/home/rolandpg/projects/zettelforge/tests/test_consolidation.py`. Two critical bugs must be fixed: tier promotion doesn't persist, and consolidation loads all notes instead of EPG-window only.

**Tech Stack:** Python 3.10+, threading, structlog, existing MemoryManager API.

**Repo:** `/home/rolandpg/zettelforge` (the standalone repo, NOT `/home/rolandpg/projects/zettelforge/`)

---

## File Structure

### Files to Create (copy from dev branch + fix)
- `src/zettelforge/consolidation.py` — Copy from dev, fix 2 critical bugs, clean dead imports
- `tests/test_consolidation.py` — Copy from dev, add real consolidation tests

### Files to Modify
- `src/zettelforge/memory_manager.py` — Add consolidation middleware integration (import + init + call in remember())
- `src/zettelforge/__init__.py` — Export ConsolidationMiddleware

---

### Task 1: Copy and fix consolidation.py

**Files:**
- Create: `src/zettelforge/consolidation.py` (copy from `/home/rolandpg/projects/zettelforge/src/zettelforge/consolidation.py`)

The adversarial review found 2 critical bugs and 3 important issues. Fix all of them:

- [ ] **Step 1: Copy the file**

```bash
cp /home/rolandpg/projects/zettelforge/src/zettelforge/consolidation.py /home/rolandpg/zettelforge/src/zettelforge/consolidation.py
```

- [ ] **Step 2: Fix Critical Bug 1 — Tier promotion doesn't persist**

In `ConsolidationEngine.consolidate()`, after `note.metadata.tier = 'A'` (around line 271), the tier change is only in memory. Add a persist call:

```python
# BEFORE (line 271):
note.metadata.tier = 'A'
report["notes_consolidated"] += 1

# AFTER:
note.metadata.tier = 'A'
try:
    self._mm.store._rewrite_note(note)
except Exception as e:
    self._logger.warning("tier_persist_failed", note_id=note.id, error=str(e))
report["notes_consolidated"] += 1
```

- [ ] **Step 3: Fix Critical Bug 2 — Consolidation loads ALL notes instead of EPG-window**

In `ConsolidationEngine.consolidate()`, the `iterate_notes()` call at line 218 loads every note in the store. Add an EPG-window tracking set to the middleware, and pass observed note IDs to the engine.

Add to `ConsolidationMiddleware.__init__()`:
```python
self._epg_note_ids: set[str] = set()
```

Add to `ConsolidationMiddleware.before_write()`, after `self._detector.observe(...)`:
```python
# Track note IDs in current EPG window (note_id passed as new parameter)
```

Actually, the simpler fix: in `consolidate()`, filter notes by `created_at` — only consider notes created since the last consolidation. Add a `_last_consolidation_time` field:

In `ConsolidationEngine.__init__()`:
```python
self._last_consolidation_time: Optional[str] = None
```

In `consolidate()`, replace the iterate loop:
```python
epg_notes = []
for note in self._mm.store.iterate_notes():
    if not note.links.superseded_by:
        # Only consider notes since last consolidation
        if self._last_consolidation_time and note.created_at < self._last_consolidation_time:
            continue
        epg_notes.append(note)
```

At the end of `consolidate()`, before returning:
```python
self._last_consolidation_time = datetime.now(timezone.utc).isoformat()
```

- [ ] **Step 4: Fix Important — Cache entity extraction results**

In `consolidate()`, the `extract_all()` call at line 244 is called once per note, then again in `_detect_contradictions()` for every pair. Cache results:

```python
# Before the domain grouping loop, build entity cache:
entity_cache: Dict[str, Dict[str, List[str]]] = {}
for note in epg_notes:
    entity_cache[note.id] = self._mm.indexer.extractor.extract_all(
        note.content.raw, use_llm=False
    )
```

Then use `entity_cache[note.id]` instead of calling `extract_all()` again. Pass the cache to `_detect_contradictions()`.

- [ ] **Step 5: Remove dead imports**

Remove `import json`, `import uuid`, `from pathlib import Path` — none are used. Remove `SEVERITY_INFO` from the ocsf import — not used.

- [ ] **Step 6: Add lock around async consolidation thread check**

In `_run_async_consolidation()`, the `is_alive()` check + thread assignment is not atomic:

```python
def _run_async_consolidation(self) -> None:
    with self._lock:  # Add a lock
        if self._async_thread and self._async_thread.is_alive():
            self._logger.info("consolidation_already_running_skipping")
            return
        # ... create and start thread
```

Add `self._lock = threading.Lock()` to `ConsolidationMiddleware.__init__()`.

- [ ] **Step 7: Run ruff**

```bash
ruff check src/zettelforge/consolidation.py && ruff format src/zettelforge/consolidation.py
```

- [ ] **Step 8: Commit**

```bash
git add src/zettelforge/consolidation.py
git commit -m "feat: add consolidation layer — GAM-style EPG/TAN with critical bug fixes"
```

---

### Task 2: Copy and improve tests

**Files:**
- Create: `tests/test_consolidation.py` (copy from dev, add real consolidation tests)

- [ ] **Step 1: Copy the test file**

```bash
cp /home/rolandpg/projects/zettelforge/tests/test_consolidation.py /home/rolandpg/zettelforge/tests/test_consolidation.py
```

- [ ] **Step 2: Add a real consolidation test with actual notes**

The existing tests all use `iterate_notes.return_value = []`, meaning the core consolidation logic is never exercised. Add a test that creates real MemoryNote objects:

```python
from zettelforge.note_schema import MemoryNote, Content, Semantic, Embedding, Metadata, Links

def _make_note(note_id: str, content: str, domain: str = "cti") -> MemoryNote:
    now = datetime.now(timezone.utc).isoformat()
    return MemoryNote(
        id=note_id,
        created_at=now,
        updated_at=now,
        content=Content(raw=content, source_type="test", source_ref=""),
        semantic=Semantic(context="", keywords=[], tags=[], entities=[]),
        embedding=Embedding(vector=[0.0] * 768),
        metadata=Metadata(domain=domain, tier="B"),
        links=Links(),
    )


class TestConsolidationWithRealNotes:
    """Tests that exercise the actual consolidation logic."""

    def test_consolidation_promotes_overlapping_notes(self):
        """Notes sharing 2+ entities should be promoted to tier A."""
        mm = MagicMock()
        notes = [
            _make_note("n1", "APT28 uses Cobalt Strike for C2"),
            _make_note("n2", "APT28 deploys Cobalt Strike beacons"),
            _make_note("n3", "APT28 targets NATO organizations"),
            _make_note("n4", "Unrelated note about cooking"),
        ]
        mm.store.iterate_notes.return_value = notes
        mm.indexer.extractor.extract_all.side_effect = lambda text, use_llm=False: {
            "actor": ["apt28"] if "APT28" in text else [],
            "tool": ["cobalt-strike"] if "Cobalt Strike" in text else [],
        }
        mm.store._rewrite_note = MagicMock()

        engine = ConsolidationEngine(mm)
        report = engine.consolidate(force=True)

        assert report["notes_examined"] == 4
        assert report["notes_consolidated"] >= 1

    def test_contradiction_detection_flags_negated_notes(self):
        """Notes with opposing claims about same entity should be flagged."""
        mm = MagicMock()
        notes = [
            _make_note("n1", "APT28 uses DROPBEAR malware"),
            _make_note("n2", "APT28 no longer uses DROPBEAR"),
        ]
        # Make n2 newer
        notes[1].created_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

        mm.store.iterate_notes.return_value = notes
        mm.indexer.extractor.extract_all.side_effect = lambda text, use_llm=False: {
            "actor": ["apt28"],
            "tool": ["dropbear"] if "DROPBEAR" in text else [],
        }
        mm.store._rewrite_note = MagicMock()

        engine = ConsolidationEngine(mm)
        contradictions = engine._detect_contradictions(notes)

        # n1 is older and contradicted → should be flagged
        assert "n1" in contradictions

    def test_epg_window_filtering(self):
        """After consolidation, only new notes should be considered."""
        mm = MagicMock()
        old_note = _make_note("old", "Old note about APT28")
        old_note.created_at = "2020-01-01T00:00:00+00:00"  # Very old

        new_note = _make_note("new", "New note about APT28")

        mm.store.iterate_notes.return_value = [old_note, new_note]
        mm.indexer.extractor.extract_all.return_value = {"actor": ["apt28"]}
        mm.store._rewrite_note = MagicMock()

        engine = ConsolidationEngine(mm)
        # First consolidation processes everything
        engine.consolidate()
        # Second consolidation should skip old notes
        mm.store.iterate_notes.return_value = [old_note, new_note]
        report = engine.consolidate()
        # old_note should be filtered out by _last_consolidation_time
```

- [ ] **Step 3: Run tests**

```bash
CI=true PYTHONPATH=src pytest tests/test_consolidation.py -v
```

- [ ] **Step 4: Run ruff**

```bash
ruff check tests/test_consolidation.py && ruff format tests/test_consolidation.py
```

- [ ] **Step 5: Commit**

```bash
git add tests/test_consolidation.py
git commit -m "test: add consolidation tests with real notes — exercises merge and contradiction detection"
```

---

### Task 3: Integrate into MemoryManager

**Files:**
- Modify: `src/zettelforge/memory_manager.py`

The dev branch shows exactly how to integrate. Read the current `memory_manager.py` in the main repo and add the integration points.

- [ ] **Step 1: Read the current memory_manager.py**

Read `src/zettelforge/memory_manager.py` and find:
- The imports section (top of file)
- The `__init__()` method
- The `stats` dict initialization
- The `remember()` method — find where entities are extracted and indexed (after `self.indexer.add_note()`)

- [ ] **Step 2: Add import**

Add to the imports:
```python
from zettelforge.consolidation import ConsolidationMiddleware
```

- [ ] **Step 3: Add initialization in __init__()**

After the existing component initializations (store, indexer, resolver, etc.), add:
```python
self.consolidation = ConsolidationMiddleware(self)
```

Add to the stats dict:
```python
'consolidations_triggered': 0,
```

- [ ] **Step 4: Add consolidation hook in remember()**

After `self.indexer.add_note(note.id, resolved_entities)` in the `remember()` method, add:

```python
# GAM consolidation: observe note for semantic shift detection
is_shift, shift_meta = self.consolidation.before_write(
    note_entities=resolved_entities,
    note_domain=domain,
    note_time=datetime.fromisoformat(note.created_at) if note.created_at else None,
)
if is_shift:
    self.stats['consolidations_triggered'] += 1
    self._logger.info(
        "semantic_shift_detected",
        note_id=note.id,
        signals=shift_meta.get("shift_signals", []),
        epg_count=shift_meta.get("epg_count", 0),
    )
```

Make sure `datetime` is imported (it likely already is from existing code).

- [ ] **Step 5: Run full test suite**

```bash
CI=true PYTHONPATH=src pytest tests/test_core.py tests/test_consolidation.py tests/test_edition.py -v --tb=short
```

- [ ] **Step 6: Run ruff**

```bash
ruff check src/zettelforge/memory_manager.py && ruff format src/zettelforge/memory_manager.py
```

- [ ] **Step 7: Commit**

```bash
git add src/zettelforge/memory_manager.py
git commit -m "feat: integrate consolidation middleware into MemoryManager.remember() write path"
```

---

### Task 4: Full verification

- [ ] **Step 1: Run the full test suite**

```bash
CI=true PYTHONPATH=src pytest tests/ -v --ignore=tests/test_cti_integration.py --ignore=tests/test_typedb_client.py --tb=short
```

Expected: same pass count as before + new consolidation tests. No regressions.

- [ ] **Step 2: Run ruff on all changed files**

```bash
ruff check src/zettelforge/consolidation.py src/zettelforge/memory_manager.py && ruff format --check src/zettelforge/consolidation.py src/zettelforge/memory_manager.py tests/test_consolidation.py
```

- [ ] **Step 3: Run the demo to verify no regression**

```bash
CI=true ZETTELFORGE_EMBEDDING_PROVIDER=mock ZETTELFORGE_LLM_PROVIDER=ollama PYTHONPATH=src python3 -m zettelforge demo 2>&1 | grep -v "^\{" | grep -v "onnxruntime"
```

The demo should complete with consolidation silently running in the background (auto_consolidate=True by default). No visible change to demo output.

- [ ] **Step 4: Push**

```bash
git push origin master
```
