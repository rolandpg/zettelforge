"""Regression tests for RFC-001 Warnings 4, 5, 6.

W-4 — `save()` truncates before flock. Atomic write via temp+rename is
       what we ship now; the test exercises that the file is never left
       in a torn state when an exception fires mid-write.
W-5 — `remove_note()` deleted entity-type keys when their dict went
       empty, breaking the 19-type invariant the indexer set up at
       __init__. Test asserts the type-bucket survives an empty.
W-6 — `_flush_sync()` was not thread-safe on `self.index`. The dict
       comprehension in `save()` could race with concurrent
       `add_note()` mutations. Test runs both concurrently with a
       lot of churn and asserts no exception escapes.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path

import pytest

from zettelforge.entity_indexer import EntityExtractor, EntityIndexer


@pytest.fixture()
def indexer(tmp_path: Path) -> EntityIndexer:
    """Fresh indexer pointed at a tmp file."""
    idx = EntityIndexer(index_path=str(tmp_path / "entity_index.json"))
    yield idx
    # Tear down any pending flush timer so the test process exits clean.
    try:
        if idx._flush_timer is not None:
            idx._flush_timer.cancel()
    except Exception:
        pass


# ── W-4: atomic save ──────────────────────────────────────────────────────


class TestSaveAtomicity:
    def test_save_writes_complete_json(self, indexer: EntityIndexer):
        indexer.add_note("note_a", {"actor": ["APT28"], "tool": ["Cobalt Strike"]})
        indexer.save()

        # File exists and is valid JSON
        assert indexer.index_path.exists()
        with open(indexer.index_path) as f:
            data = json.load(f)
        assert "actor" in data
        assert "apt28" in data["actor"]
        assert "note_a" in data["actor"]["apt28"]

    def test_save_does_not_leave_temp_files_on_success(
        self, indexer: EntityIndexer, tmp_path: Path
    ):
        indexer.add_note("note_a", {"actor": ["APT28"]})
        indexer.save()
        leftovers = [p for p in tmp_path.iterdir() if p.name.startswith(".entity_index.")]
        assert leftovers == [], f"Temp files left behind: {leftovers}"

    def test_save_cleans_up_temp_file_on_serialize_failure(
        self, indexer: EntityIndexer, tmp_path: Path, monkeypatch
    ):
        indexer.add_note("note_a", {"actor": ["APT28"]})

        # Force json.dump to raise mid-write.
        def _boom(*_args, **_kwargs):
            raise RuntimeError("simulated FS error")

        monkeypatch.setattr("zettelforge.entity_indexer.json.dump", _boom)
        with pytest.raises(RuntimeError):
            indexer.save()

        leftovers = [p for p in tmp_path.iterdir() if p.name.startswith(".entity_index.")]
        assert leftovers == [], f"Temp file not cleaned: {leftovers}"

    def test_save_uses_atomic_rename_pattern(
        self, indexer: EntityIndexer, tmp_path: Path, monkeypatch
    ):
        """The final write must go through os.replace (atomic on POSIX),
        not a direct open-in-write-mode that would truncate before flock."""
        observed_replaces = []
        real_replace = os.replace

        def _spy(src, dst):
            observed_replaces.append((str(src), str(dst)))
            return real_replace(src, dst)

        monkeypatch.setattr("zettelforge.entity_indexer.os.replace", _spy)

        indexer.add_note("note_a", {"actor": ["APT28"]})
        indexer.save()

        assert any(str(indexer.index_path) == dst for _, dst in observed_replaces), (
            f"Expected os.replace to land on {indexer.index_path}; observed: {observed_replaces}"
        )


# ── W-5: 19-type invariant ───────────────────────────────────────────────


class TestEntityTypeInvariant:
    def test_remove_note_preserves_empty_type_bucket(self, indexer: EntityIndexer):
        # Set up: indexer starts with all ENTITY_TYPES keys, empty dicts.
        all_types_before = set(indexer.index.keys())
        assert all_types_before == set(EntityExtractor.ENTITY_TYPES)

        # Add then remove a note that touched 'actor' and 'tool'.
        indexer.add_note("note_a", {"actor": ["APT28"], "tool": ["Cobalt Strike"]})
        indexer.remove_note("note_a")

        # Both type buckets must still exist (empty), per RFC-001 W-5.
        assert "actor" in indexer.index, (
            "Removing the last note must NOT delete the entity-type key"
        )
        assert "tool" in indexer.index
        assert indexer.index["actor"] == {}, "Empty bucket should be a present-but-empty dict"
        assert indexer.index["tool"] == {}

        # Full invariant survives.
        assert set(indexer.index.keys()) == set(EntityExtractor.ENTITY_TYPES)

    def test_remove_note_prunes_empty_per_value_sets(self, indexer: EntityIndexer):
        """Per-value dicts SHOULD be cleaned when their note-set empties —
        only the parent type-bucket is preserved."""
        indexer.add_note("note_a", {"actor": ["APT28"]})
        assert "apt28" in indexer.index["actor"]
        indexer.remove_note("note_a")
        assert "apt28" not in indexer.index["actor"], (
            "Empty per-value sets should be pruned to keep the index compact"
        )


# ── W-6: thread-safety on save ↔ add_note ────────────────────────────────


class TestConcurrentSaveAndMutate:
    def test_save_during_concurrent_add_does_not_raise(self, indexer: EntityIndexer):
        """Drive save() and add_note() concurrently with churn. Without
        the W-6 fix this raised RuntimeError: dictionary changed size
        during iteration. With the fix the lock serializes them."""
        errors: list[BaseException] = []
        stop = threading.Event()

        def writer():
            i = 0
            while not stop.is_set() and i < 500:
                try:
                    indexer.add_note(
                        f"note_{i}",
                        {"actor": [f"APT{i % 5}"], "tool": [f"tool{i % 7}"]},
                    )
                except BaseException as exc:  # noqa: BLE001 — capture for the assert
                    errors.append(exc)
                    return
                i += 1

        def saver():
            j = 0
            while not stop.is_set() and j < 50:
                try:
                    indexer.save()
                except BaseException as exc:  # noqa: BLE001
                    errors.append(exc)
                    return
                j += 1

        t1 = threading.Thread(target=writer)
        t2 = threading.Thread(target=saver)
        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)
        stop.set()

        assert errors == [], f"Concurrent save+add raised: {errors[0]!r}"
        # Final state is internally consistent.
        assert "actor" in indexer.index
        assert all(isinstance(v, dict) for v in indexer.index.values())

    def test_flush_sync_clears_dirty_flag(self, indexer: EntityIndexer):
        """_flush_sync must clear self._dirty even under the new locking."""
        indexer.add_note("note_a", {"actor": ["APT28"]})
        assert indexer._dirty is True
        indexer._flush_sync()
        assert indexer._dirty is False
