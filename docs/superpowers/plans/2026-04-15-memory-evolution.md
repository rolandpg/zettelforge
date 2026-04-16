# Implementation Plan: Memory Evolution (Feature 4)

**Date:** 2026-04-15
**Estimated effort:** 3-4 days
**Branch:** `feat/memory-evolution`

## Goal

Add a `MemoryEvolver` that finds top-k semantic neighbors for a note, uses the LLM to synthesize an evolved version incorporating neighbor context, and persists the update with rollback capability. Runs on the existing enrichment queue to prevent race conditions.

## Architecture Decisions

### AD-1: Evolution runs on the existing enrichment queue

No separate thread. The `_EnrichmentJob` dataclass gains a `job_type` field: `"causal_extraction"` (existing default) or `"neighbor_evolution"` (new). `_enrichment_loop` dispatches based on `job_type`. One job at a time -- no races between evolution and causal extraction.

### AD-2: LLM parameters

- `max_tokens=1024` (not 300 -- evolution output is longer than extraction)
- `json_mode=True` via `generate()`
- Parse with `json_parse.extract_json(output, expect="object")`
- Single retry on parse failure (call generate again once)

### AD-3: Original content preserved

New field `previous_raw` on the `Content` dataclass. Before overwriting `content.raw`, copy current value to `content.previous_raw`. This enables rollback without a separate history table.

### AD-4: No cascading evolution

Notes being evolved are marked with `_evolution_in_progress=True` (transient, in-memory flag on the job). The evolver skips notes that are already queued for evolution. `evolution_count > 0` is the persistent signal that a note has been evolved (not `evolved_from = self.id`).

### AD-5: Re-embedding on evolution

After updating `content.raw`, call `get_embedding()` on the new content and upsert into LanceDB. Without this, vector search returns stale results.

## Tasks

### Task 1: Extend Content dataclass (0.25 day)

**Files:**
- `src/zettelforge/note_schema.py`

**Steps:**

1. Add `previous_raw` field to `Content`:

```python
class Content(BaseModel):
    """Raw content and source metadata"""
    raw: str
    source_type: str
    source_ref: str
    previous_raw: Optional[str] = None  # Preserved before evolution for rollback
```

2. Import `Optional` at top if not already present (it is).

**Test:**
```bash
python -m pytest tests/ -k "test_note_schema or test_memory_note" -x
```

### Task 2: Extend enrichment queue with job types (0.5 day)

**Files:**
- `src/zettelforge/memory_manager.py`

**Steps:**

1. Add `job_type` to `_EnrichmentJob`:

```python
@dataclass
class _EnrichmentJob:
    """Work item for the slow-path enrichment worker."""
    note_id: str
    domain: str
    content_len: int
    resolved_entities: dict = field(default_factory=dict)
    job_type: str = "causal_extraction"  # or "neighbor_evolution"
```

2. Update `_enrichment_loop` to dispatch:

```python
def _enrichment_loop(self) -> None:
    while True:
        try:
            job = self._enrichment_queue.get(timeout=1.0)
            if job.job_type == "neighbor_evolution":
                self._run_evolution(job)
            else:
                self._run_enrichment(job)
            self._enrichment_queue.task_done()
        except queue.Empty:
            continue
        except Exception:
            self._logger.error("enrichment_worker_error", exc_info=True)
```

**Test:**
```bash
python -m pytest tests/ -k "test_enrichment" -x
```

### Task 3: Implement MemoryEvolver (1.5 days)

**Files:**
- `src/zettelforge/memory_evolver.py` (new file)

**Steps:**

1. Create `MemoryEvolver` class:

```python
"""
Memory Evolver - LLM-driven note evolution via neighbor synthesis.

Finds top-k semantic neighbors, synthesizes an evolved version,
and persists with rollback capability.
"""

from typing import Dict, List, Optional, Tuple

from zettelforge.json_parse import extract_json
from zettelforge.llm_client import generate
from zettelforge.log import get_logger
from zettelforge.note_schema import MemoryNote
from zettelforge.vector_memory import get_embedding

_logger = get_logger("zettelforge.evolver")

EVOLUTION_PROMPT = """You are a memory evolution agent. Given a source note and its semantic neighbors, synthesize an improved version that incorporates relevant context from neighbors.

Source note:
{source_content}

Neighbor notes:
{neighbor_content}

Return JSON with these fields:
- "evolved_content": the improved note text (preserve all original facts, add context from neighbors)
- "evolution_rationale": one sentence explaining what was added
- "confidence": float 0.0-1.0, how confident the evolution improves the note

JSON:"""


class MemoryEvolver:
    """Evolve notes by synthesizing context from semantic neighbors."""

    def __init__(self, memory_store, vector_retriever):
        self.store = memory_store
        self.retriever = vector_retriever

    def find_evolution_candidates(
        self,
        note: MemoryNote,
        k: int = 5,
        min_similarity: float = 0.3,
    ) -> List[MemoryNote]:
        """Find top-k semantic neighbors suitable for evolution."""
        results = self.retriever.retrieve(
            query=note.content.raw[:500],
            domain=note.metadata.domain,
            k=k + 1,  # +1 because the note itself may appear
            include_links=False,
        )
        # Exclude self and already-evolving notes
        candidates = [
            r for r in results
            if r.id != note.id
        ]
        return candidates[:k]

    def evolve(
        self, note: MemoryNote, neighbors: List[MemoryNote]
    ) -> Optional[Dict]:
        """
        Use LLM to evolve a note with neighbor context.

        Returns dict with evolved_content, evolution_rationale, confidence
        or None on failure.
        """
        neighbor_text = "\n---\n".join(
            f"[{n.id}] {n.content.raw[:300]}" for n in neighbors[:5]
        )

        prompt = EVOLUTION_PROMPT.format(
            source_content=note.content.raw[:1000],
            neighbor_content=neighbor_text,
        )

        # First attempt
        output = generate(prompt, max_tokens=1024, temperature=0.2, json_mode=True)
        result = extract_json(output, expect="object")

        # Single retry on parse failure
        if result is None:
            _logger.warning("evolution_parse_retry", note_id=note.id)
            output = generate(prompt, max_tokens=1024, temperature=0.1, json_mode=True)
            result = extract_json(output, expect="object")

        if result is None:
            _logger.warning("evolution_parse_failed", note_id=note.id)
            return None

        # Validate required fields
        if "evolved_content" not in result:
            _logger.warning("evolution_missing_content", note_id=note.id)
            return None

        return result

    def apply_evolution(
        self, note: MemoryNote, evolution: Dict
    ) -> MemoryNote:
        """
        Apply evolution result to a note. Preserves original in previous_raw.
        Re-embeds and updates metadata.
        """
        evolved_content = evolution["evolved_content"]
        confidence = float(evolution.get("confidence", 0.8))

        # Preserve original content for rollback
        note.content.previous_raw = note.content.raw
        note.content.raw = evolved_content

        # Update metadata
        note.metadata.evolution_count += 1
        note.metadata.confidence = min(note.metadata.confidence, confidence)

        # Re-embed with new content
        new_vector = get_embedding(evolved_content[:1000])
        note.embedding.vector = new_vector

        return note

    def rollback(self, note: MemoryNote) -> bool:
        """Rollback to previous content if available."""
        if note.content.previous_raw is None:
            return False
        note.content.raw = note.content.previous_raw
        note.content.previous_raw = None
        note.metadata.evolution_count = max(0, note.metadata.evolution_count - 1)
        # Re-embed with restored content
        note.embedding.vector = get_embedding(note.content.raw[:1000])
        return True
```

**Test:**
```bash
python -m pytest tests/ -k "test_evolver" -x
```

### Task 4: Wire evolution into MemoryManager (1 day)

**Files:**
- `src/zettelforge/memory_manager.py`

**Steps:**

1. Add `_run_evolution()` method to `MemoryManager`:

```python
def _run_evolution(self, job: _EnrichmentJob) -> None:
    """Execute neighbor evolution for one note."""
    note = self.store.get_note_by_id(job.note_id)
    if note is None:
        self._pending_enrichment.discard(job.note_id)
        return

    try:
        from zettelforge.memory_evolver import MemoryEvolver

        evolver = MemoryEvolver(
            memory_store=self.store,
            vector_retriever=self.retriever,
        )
        neighbors = evolver.find_evolution_candidates(note, k=5)
        if len(neighbors) < 2:
            self._logger.info("evolution_insufficient_neighbors", note_id=note.id)
            return

        evolution = evolver.evolve(note, neighbors)
        if evolution is None:
            return

        confidence = float(evolution.get("confidence", 0.0))
        if confidence < 0.5:
            self._logger.info(
                "evolution_low_confidence",
                note_id=note.id,
                confidence=confidence,
            )
            return

        evolver.apply_evolution(note, evolution)

        # Persist: rewrite JSONL + upsert LanceDB
        self.store._rewrite_note(note)
        if self.store.lancedb is not None:
            self.store._upsert_lancedb(note)

        self._logger.info(
            "note_evolved",
            note_id=note.id,
            evolution_count=note.metadata.evolution_count,
            rationale=evolution.get("evolution_rationale", "")[:100],
        )
    except Exception:
        self._logger.warning("evolution_failed", note_id=note.id, exc_info=True)
    finally:
        self._pending_enrichment.discard(job.note_id)
```

2. Add public `evolve_note()` method:

```python
def evolve_note(self, note_id: str, sync: bool = False) -> bool:
    """
    Queue a note for neighbor-based evolution.

    Args:
        note_id: ID of the note to evolve.
        sync: If True, run evolution inline (blocking).

    Returns:
        True if queued/executed, False if note not found or already pending.
    """
    if note_id in self._pending_enrichment:
        return False

    note = self.store.get_note_by_id(note_id)
    if note is None:
        return False

    job = _EnrichmentJob(
        note_id=note_id,
        domain=note.metadata.domain,
        content_len=len(note.content.raw),
        job_type="neighbor_evolution",
    )

    if sync:
        self._run_evolution(job)
        return True

    try:
        self._enrichment_queue.put_nowait(job)
        self._pending_enrichment.add(note_id)
        return True
    except queue.Full:
        self._logger.warning("enrichment_queue_full", note_id=note_id)
        return False
```

**Test:**
```bash
python -m pytest tests/ -k "test_memory_manager" -x
python -m pytest tests/ -k "test_evolve" -x
```

### Task 5: Tests (0.5 day)

**Files:**
- `tests/test_memory_evolver.py` (new)

**Steps:**

1. Unit test `MemoryEvolver.evolve()` with mocked LLM that returns valid JSON.
2. Unit test `apply_evolution()` preserves `previous_raw`.
3. Unit test `rollback()` restores original content and re-embeds.
4. Integration test: `MemoryManager.evolve_note(sync=True)` on a note with neighbors.
5. Test that evolution jobs and causal extraction jobs do not race (sequential queue processing).

## Commits

1. `feat(schema): add Content.previous_raw for evolution rollback`
2. `feat(queue): add job_type to enrichment queue for evolution dispatch`
3. `feat(evolver): MemoryEvolver with LLM synthesis and rollback`
4. `feat(manager): wire evolve_note() through enrichment queue`

## Risks

- **LLM hallucination:** Evolution may introduce false facts. The `confidence` gate at 0.5 and `previous_raw` rollback mitigate but do not eliminate this.
- **Embedding drift:** Repeated evolution may drift embeddings away from original meaning. `evolution_count > 5` triggers `should_flag_for_review()` (already implemented).
- **Queue depth:** Large batches of evolution jobs could starve causal extraction. Consider priority queueing in a future pass if this becomes a problem.
