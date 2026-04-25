"""Tests for RFC-009 Phase 1.5 — LanceDB version-cleanup daemon."""

from __future__ import annotations

import threading
import time
from datetime import timedelta
from pathlib import Path
from unittest.mock import MagicMock

from zettelforge.lance_maintenance import (
    LanceVersionMaintenance,
    _extract_versions_pruned,
    _safe_dir_size,
)

# ── Helpers ──────────────────────────────────────────────────────────────


class _StubTable:
    """Records cleanup_old_versions invocations."""

    def __init__(self) -> None:
        self.calls: list[timedelta] = []
        self.exception: Exception | None = None
        self.stats = MagicMock(old_versions=3)

    def cleanup_old_versions(self, older_than: timedelta):
        self.calls.append(older_than)
        if self.exception is not None:
            raise self.exception
        return self.stats


class _StubDB:
    def __init__(self) -> None:
        self.tables: dict[str, _StubTable] = {}

    def open_table(self, name: str) -> _StubTable:
        if name not in self.tables:
            self.tables[name] = _StubTable()
        return self.tables[name]


# ── _extract_versions_pruned ─────────────────────────────────────────────


class TestExtractVersionsPruned:
    def test_picks_old_versions_attribute_when_present(self):
        stats = MagicMock(spec=["old_versions"])
        stats.old_versions = 7
        assert _extract_versions_pruned(stats) == 7

    def test_falls_back_to_versions_removed(self):
        stats = MagicMock(spec=["versions_removed"])
        stats.versions_removed = 4
        assert _extract_versions_pruned(stats) == 4

    def test_returns_none_when_unknown_shape(self):
        stats = MagicMock(spec=["nothing_useful_here"])
        assert _extract_versions_pruned(stats) is None

    def test_returns_none_when_stats_is_none(self):
        assert _extract_versions_pruned(None) is None


# ── _safe_dir_size ────────────────────────────────────────────────────────


class TestSafeDirSize:
    def test_missing_path_returns_zero(self):
        assert _safe_dir_size(Path("/nonexistent/zf-test-path-xyz")) == 0

    def test_none_path_returns_zero(self):
        assert _safe_dir_size(None) == 0

    def test_sums_files_recursively(self, tmp_path):
        (tmp_path / "a.lance").write_bytes(b"x" * 100)
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "b.lance").write_bytes(b"y" * 50)
        assert _safe_dir_size(tmp_path) == 150


# ── Daemon behavior — direct _run_one() tests (no threading) ─────────────


class TestRunOne:
    """Drive _run_one() directly to test the cleanup-iteration logic
    without spawning threads or waiting on real time."""

    def _make(
        self,
        db,
        interval: int = 60,
        older_than: int = 3600,
        table_root=None,
    ):
        return LanceVersionMaintenance(
            db=db,
            interval_minutes_provider=lambda: interval,
            older_than_seconds_provider=lambda: older_than,
            table_root=table_root,
        )

    def test_calls_cleanup_with_configured_older_than(self):
        db = _StubDB()
        maint = self._make(db, older_than=7200)
        maint._run_one("notes_cti")
        assert len(db.tables["notes_cti"].calls) == 1
        assert db.tables["notes_cti"].calls[0] == timedelta(seconds=7200)

    def test_skips_when_older_than_is_zero(self):
        db = _StubDB()
        maint = self._make(db, older_than=0)
        maint._run_one("notes_cti")
        assert "notes_cti" not in db.tables  # never opened

    def test_swallows_lance_exceptions(self):
        db = _StubDB()
        # Force the exception on first call
        db.open_table("notes_cti").exception = RuntimeError("transient FS error")
        maint = self._make(db)
        # Must not raise
        maint._run_one("notes_cti")
        # Subsequent successful calls still work — daemon doesn't get stuck
        db.tables["notes_cti"].exception = None
        maint._run_one("notes_cti")
        assert len(db.tables["notes_cti"].calls) == 2

    def test_negative_older_than_clamped_to_zero(self):
        db = _StubDB()
        maint = self._make(db, older_than=-1)
        maint._run_one("notes_cti")
        # Negative clamps to 0 → skipped, no open_table call
        assert "notes_cti" not in db.tables


# ── register_table — idempotency + interval-zero gate ────────────────────


class TestRegisterTable:
    def _make_silent(self, db, interval: int = 60):
        # Use an Event-based sleep so register_table starts a thread we
        # can quickly tear down without waiting on real time.
        stop = threading.Event()

        def fake_sleep(_seconds):
            stop.wait(timeout=0.05)

        maint = LanceVersionMaintenance(
            db=db,
            interval_minutes_provider=lambda: interval,
            older_than_seconds_provider=lambda: 3600,
            sleep=fake_sleep,
        )
        return maint, stop

    def test_skipped_when_db_is_none(self):
        maint, _ = self._make_silent(db=None)
        maint.register_table("notes_cti")
        assert "notes_cti" not in maint._threads

    def test_skipped_when_interval_zero(self):
        maint, _ = self._make_silent(db=_StubDB(), interval=0)
        maint.register_table("notes_cti")
        assert "notes_cti" not in maint._threads

    def test_idempotent_for_same_table(self):
        maint, stop = self._make_silent(db=_StubDB())
        try:
            maint.register_table("notes_cti")
            t1 = maint._threads["notes_cti"]
            maint.register_table("notes_cti")  # second call
            t2 = maint._threads["notes_cti"]
            assert t1 is t2  # same thread object
        finally:
            stop.set()
            maint.stop(timeout=0.5)


# ── start() discovery ────────────────────────────────────────────────────


class TestStart:
    def test_no_op_when_db_is_none(self, tmp_path):
        maint = LanceVersionMaintenance(
            db=None,
            interval_minutes_provider=lambda: 60,
            older_than_seconds_provider=lambda: 3600,
            table_root=tmp_path,
        )
        maint.start()
        assert maint._threads == {}

    def test_no_op_when_interval_zero(self, tmp_path):
        (tmp_path / "notes_cti.lance").mkdir()
        maint = LanceVersionMaintenance(
            db=_StubDB(),
            interval_minutes_provider=lambda: 0,
            older_than_seconds_provider=lambda: 3600,
            table_root=tmp_path,
        )
        maint.start()
        assert maint._threads == {}

    def test_discovers_existing_lance_directories(self, tmp_path):
        (tmp_path / "notes_cti.lance").mkdir()
        (tmp_path / "notes_general.lance").mkdir()
        (tmp_path / "ignored_file.txt").write_text("not a table")
        (tmp_path / "ignored_subdir").mkdir()  # no .lance suffix

        maint = LanceVersionMaintenance(
            db=_StubDB(),
            interval_minutes_provider=lambda: 60,
            older_than_seconds_provider=lambda: 3600,
            table_root=tmp_path,
            sleep=lambda _: None,  # avoid real sleep in spawned threads
        )
        try:
            maint.start()
            assert set(maint._threads.keys()) == {"notes_cti", "notes_general"}
        finally:
            maint.stop(timeout=0.5)


# ── Stop signaling ────────────────────────────────────────────────────────


class TestStop:
    def test_stop_event_unblocks_thread(self):
        # Use an artificially huge interval to prove that stop_event
        # wakes the loop without us waiting through it.
        maint = LanceVersionMaintenance(
            db=_StubDB(),
            interval_minutes_provider=lambda: 9999,
            older_than_seconds_provider=lambda: 3600,
        )
        maint.register_table("notes_cti")
        t0 = time.monotonic()
        maint.stop(timeout=2.0)
        elapsed = time.monotonic() - t0
        # Must come back well before the would-be sleep
        assert elapsed < 2.0


# ── Telemetry surface ────────────────────────────────────────────────────


class TestTelemetry:
    def test_emits_lance_cleanup_old_versions_event(self, capsys, monkeypatch):
        # Capture structlog output through the standard logger
        import logging

        records: list[logging.LogRecord] = []

        class _Capture(logging.Handler):
            def emit(self, record):  # noqa: D401
                records.append(record)

        target = logging.getLogger("zettelforge.lance_maintenance")
        handler = _Capture()
        target.addHandler(handler)
        target.setLevel(logging.DEBUG)
        try:
            db = _StubDB()
            maint = LanceVersionMaintenance(
                db=db,
                interval_minutes_provider=lambda: 60,
                older_than_seconds_provider=lambda: 3600,
            )
            maint._run_one("notes_cti")
        finally:
            target.removeHandler(handler)

        assert any(
            "lance_cleanup_old_versions" in str(r.msg)
            or "lance_cleanup_old_versions" in str(r.args)
            for r in records
        ) or any(getattr(r, "event", None) == "lance_cleanup_old_versions" for r in records)
