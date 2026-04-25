"""
GOV-012 Logging Compliance Tests

Ensures:
- No print() in production code
- Core operations emit OCSF events with required fields
- LanceDB failures are logged, not swallowed (regression for #26)
- Governance violations emit Authorization events
- Audit events reach the audit log
"""

import ast
import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest
import structlog

from zettelforge.memory_store import MemoryStore
from zettelforge.note_schema import MemoryNote, Content, Semantic, Embedding, Metadata
from zettelforge.ocsf import (
    log_api_activity,
    log_authorization,
    log_authentication,
    log_config_change,
    STATUS_SUCCESS,
    STATUS_FAILURE,
    SEVERITY_HIGH,
)

NOW = datetime.now().isoformat()


def _make_note(note_id: str = "test_log_1", domain: str = "cti") -> MemoryNote:
    return MemoryNote(
        id=note_id,
        created_at=NOW,
        updated_at=NOW,
        content=Content(raw="Test content for logging", source_type="test", source_ref=""),
        semantic=Semantic(context="ctx", keywords=["test"], tags=[], entities=[]),
        embedding=Embedding(vector=[0.0] * 768),
        metadata=Metadata(domain=domain),
    )


class TestNoPrintInProduction:
    """Scan src/zettelforge/ for print() calls outside __main__ blocks."""

    def _find_print_calls(self, filepath: Path) -> list[int]:
        """Return line numbers of print() calls not inside if __name__ blocks."""
        source = filepath.read_text()
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return []

        main_guard_lines: set[int] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                # Detect if __name__ == "__main__":
                test = node.test
                if (
                    isinstance(test, ast.Compare)
                    and isinstance(test.left, ast.Name)
                    and test.left.id == "__name__"
                ):
                    for lineno in range(node.lineno, node.end_lineno + 1):
                        main_guard_lines.add(lineno)

        violations = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id == "print":
                    if node.lineno not in main_guard_lines:
                        violations.append(node.lineno)
        return violations

    # CLI entry points that legitimately use print() for user output
    _CLI_FILES = {"__main__.py", "demo.py"}

    def test_no_print_in_production(self):
        """No print() calls in src/zettelforge/ except __main__ blocks and CLI files."""
        src_dir = Path(__file__).parent.parent / "src" / "zettelforge"
        violations = {}
        for pyfile in sorted(src_dir.glob("*.py")):
            if pyfile.name in self._CLI_FILES:
                continue
            lines = self._find_print_calls(pyfile)
            if lines:
                violations[pyfile.name] = lines

        assert violations == {}, (
            f"GOV-003 violation: print() found in production code: {violations}"
        )


class TestOCSFEventFields:
    """Verify OCSF events contain required base fields."""

    def test_api_activity_fields(self):
        """log_api_activity emits required OCSF base fields."""
        output = structlog.testing.capture_logs()
        with structlog.testing.capture_logs() as logs:
            log_api_activity(
                operation="remember",
                status_id=STATUS_SUCCESS,
                note_id="n123",
                duration_ms=42.5,
            )

        assert len(logs) >= 1
        event = logs[0]
        assert event["event"] == "ocsf_api_activity"
        assert event["class_uid"] == 6002
        assert event["status_id"] == STATUS_SUCCESS
        assert "time" in event
        assert "metadata" in event
        assert event["metadata"]["product"]["name"] == "zettelforge"

    def test_product_version_matches_pyproject(self):
        """[task #35] OCSF metadata version must track the source pyproject.toml,
        not stale importlib.metadata. Vigil 2026-04-24 emitted v2.4.1 events
        from v2.4.2 source because the editable-install metadata was stale."""
        from pathlib import Path

        from zettelforge.ocsf import _PRODUCT_VERSION

        repo_root = Path(__file__).resolve().parent.parent
        pyproject_text = (repo_root / "pyproject.toml").read_text(encoding="utf-8")
        expected = None
        for line in pyproject_text.splitlines():
            stripped = line.strip()
            if stripped.startswith("version") and "=" in stripped:
                expected = stripped.split("=", 1)[1].strip().strip('"').strip("'")
                break
        assert expected is not None, "could not find version line in pyproject.toml"
        assert _PRODUCT_VERSION == expected, (
            f"OCSF product.version={_PRODUCT_VERSION!r} drifted from "
            f"pyproject.toml version={expected!r}"
        )

    def test_authorization_deny_fields(self):
        """log_authorization with deny emits correct status and severity."""
        with structlog.testing.capture_logs() as logs:
            log_authorization(
                actor="system",
                resource="remember",
                status_id=STATUS_FAILURE,
                severity_id=SEVERITY_HIGH,
                policy="GOV-011",
            )

        assert len(logs) >= 1
        event = logs[0]
        assert event["class_uid"] == 3003
        assert event["status_id"] == STATUS_FAILURE
        assert event["severity_id"] == SEVERITY_HIGH
        assert event["policy"] == "GOV-011"


class TestLogLevelEnvVar:
    """[task #41] ZETTELFORGE_LOG_LEVEL must reach configure_logging.

    Before this fix, ``log.py:get_logger()`` always called ``configure_logging()``
    with the hardcoded default ``level='INFO'``, then locked ``_configured=True``,
    so ``config.yaml log.level=DEBUG`` was dead code. Vigil hit this on
    2026-04-24 — DEBUG was set in config but every named logger inherited INFO.
    """

    def test_get_logger_threads_env_var_into_configure(self, monkeypatch):
        import zettelforge.log as zlog

        monkeypatch.setenv("ZETTELFORGE_LOG_LEVEL", "DEBUG")
        monkeypatch.setattr(zlog, "_configured", False)

        captured = {}

        def fake_configure(level="INFO", **kwargs):
            captured["level"] = level
            zlog._configured = True

        monkeypatch.setattr(zlog, "configure_logging", fake_configure)
        zlog.get_logger("dummy.envvar")
        assert captured.get("level") == "DEBUG"

    def test_get_logger_default_level_when_env_unset(self, monkeypatch):
        import zettelforge.log as zlog

        monkeypatch.delenv("ZETTELFORGE_LOG_LEVEL", raising=False)
        monkeypatch.setattr(zlog, "_configured", False)

        captured = {}

        def fake_configure(level="INFO", **kwargs):
            captured["level"] = level
            zlog._configured = True

        monkeypatch.setattr(zlog, "configure_logging", fake_configure)
        zlog.get_logger("dummy.noenv")
        assert captured.get("level") == "INFO"


class TestEmbeddingPreload:
    """[task #39] MemoryManager.__init__ must preload fastembed.

    Without preload, the first remember() pays ~800ms in its construct phase
    while fastembed lazy-loads. RFC-009 Phase 0.5 data on Vigil showed first-call
    construct=799ms vs warm construct=37ms; this test pins the wiring.
    """

    def test_memory_manager_init_calls_preload(self, monkeypatch):
        import tempfile

        import zettelforge.memory_manager as mm_mod

        calls = []
        monkeypatch.setattr(mm_mod, "preload_embedding_model", lambda: calls.append(1))

        with tempfile.TemporaryDirectory() as tmp:
            mm_mod.MemoryManager(jsonl_path=f"{tmp}/n.jsonl", lance_path=f"{tmp}/v")

        assert len(calls) == 1, (
            "MemoryManager.__init__ must invoke preload_embedding_model() exactly once"
        )


class TestPhaseTimingsInstrumentation:
    """[RFC-009 Phase 0.5] remember() emits per-phase timers for latency attribution."""

    def test_remember_emits_phase_timings_ms(self):
        """The ocsf_api_activity event for remember() must carry phase_timings_ms
        with numeric values for each instrumented phase."""
        from zettelforge import MemoryManager

        with tempfile.TemporaryDirectory() as tmpdir:
            mm = MemoryManager(jsonl_path=f"{tmpdir}/notes.jsonl", lance_path=f"{tmpdir}/vectordb")
            with structlog.testing.capture_logs() as logs:
                mm.remember("APT28 deploys Cobalt Strike beacons", domain="cti")

        remember_events = [
            e
            for e in logs
            if e.get("event") == "ocsf_api_activity" and e.get("activity_name") == "remember"
        ]
        assert remember_events, "No ocsf_api_activity event for remember() was emitted"

        event = remember_events[-1]
        assert "phase_timings_ms" in event, (
            "phase_timings_ms missing from remember() ocsf_api_activity event"
        )
        timings = event["phase_timings_ms"]
        assert isinstance(timings, dict)

        # Phases that always run on the direct-store async path
        expected_keys = {
            "construct",
            "write_note",
            "entity_index",
            "consolidation_observe",
            "supersession",
            "kg_update",
            "enrichment_dispatch",
        }
        missing = expected_keys - set(timings)
        assert not missing, f"Missing phase timings: {missing}. Got: {set(timings)}"

        for key, value in timings.items():
            assert isinstance(value, (int, float)), (
                f"phase_timings_ms[{key!r}] is {type(value).__name__}, expected numeric"
            )
            assert value >= 0, f"phase_timings_ms[{key!r}] = {value} (negative)"

    def test_enrichment_dispatch_excluded_in_sync_mode(self):
        """In sync=True mode the dispatch bucket is intentionally omitted so
        inline LLM work is not misattributed to dispatch latency."""
        from zettelforge import MemoryManager

        with tempfile.TemporaryDirectory() as tmpdir:
            mm = MemoryManager(jsonl_path=f"{tmpdir}/notes.jsonl", lance_path=f"{tmpdir}/vectordb")
            with structlog.testing.capture_logs() as logs:
                mm.remember("APT29 phishing campaign observed", domain="cti", sync=True)

        remember_events = [
            e
            for e in logs
            if e.get("event") == "ocsf_api_activity" and e.get("activity_name") == "remember"
        ]
        assert remember_events
        timings = remember_events[-1]["phase_timings_ms"]
        assert "enrichment_dispatch" not in timings, (
            "sync=True should NOT emit enrichment_dispatch (would mix LLM work into "
            "dispatch bucket and corrupt Phase 0.5 attribution)"
        )


class TestLanceDBFailureLogged:
    """Regression test for #26: LanceDB failures must be logged, not swallowed."""

    def test_lance_indexing_failure_emits_log(self):
        """When _index_in_lance fails, a structured error is emitted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(jsonl_path=f"{tmpdir}/notes.jsonl", lance_path=f"{tmpdir}/vectordb")
            note = _make_note()

            # Sabotage the LanceDB connection to force a failure
            store._lancedb = "not_a_real_db"  # type: ignore

            with structlog.testing.capture_logs() as logs:
                store._index_in_lance(note)

            # Should have logged an error, not silently swallowed
            error_logs = [l for l in logs if l.get("log_level", "") == "error"]
            assert len(error_logs) > 0, (
                "LanceDB indexing failure was silently swallowed (regression of #26)"
            )


class TestGovernanceViolationEvent:
    """Governance violation should emit OCSF Authorization event."""

    def test_governance_violation_emits_authorization_event(self):
        """Triggering a governance violation emits an OCSF class 3003 deny event."""
        with structlog.testing.capture_logs() as logs:
            log_authorization(
                actor="system",
                resource="remember",
                status_id=STATUS_FAILURE,
                severity_id=SEVERITY_HIGH,
                policy="GOV-011",
                violation="empty_content",
            )

        auth_events = [l for l in logs if l.get("class_uid") == 3003]
        assert len(auth_events) == 1
        assert auth_events[0]["status_id"] == STATUS_FAILURE
        assert auth_events[0]["violation"] == "empty_content"
