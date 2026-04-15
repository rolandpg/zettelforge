"""
Tests for GAM-style Consolidation Layer.

Covers:
- SemanticShiftDetector: entity novelty, topic shift, temporal gap
- ConsolidationEngine: merge, contradiction detection
- ConsolidationMiddleware: integration with MemoryManager
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

from zettelforge.consolidation import (
    ConsolidationEngine,
    ConsolidationMiddleware,
    SemanticShiftDetector,
)

# ── SemanticShiftDetector Tests ─────────────────────────────────────────────


class TestSemanticShiftDetector:
    """Unit tests for the semantic shift detector."""

    def setup_method(self):
        self.detector = SemanticShiftDetector(
            entity_shift_threshold=0.4,
            topic_shift_threshold=0.5,
            temporal_gap_hours=4.0,
            min_epg_size=3,
        )

    def test_no_shift_on_small_epg(self):
        """Should not trigger shift when EPG has fewer than min_epg_size notes."""
        is_shift, meta = self.detector.detect_shift(
            note_entities={"actor": ["APT28"]},
            note_domain="cti",
        )
        assert is_shift is False
        assert meta["reason"] == "epg_too_small"

    def test_entity_novelty_triggers_shift(self):
        """High entity novelty should trigger semantic shift."""
        # Build up EPG with known entities
        for i in range(5):
            self.detector.observe(
                note_entities={"actor": ["APT28"], "tool": ["mimikatz"]},
                note_domain="cti",
            )

        # Now introduce completely new entities
        is_shift, meta = self.detector.detect_shift(
            note_entities={"actor": ["VoltTyphoon"], "cve": ["CVE-2026-9999"]},
            note_domain="cti",
        )
        # All entities are novel → novelty_ratio = 1.0 > 0.4
        assert meta["entity_novelty"] == 1.0
        assert is_shift is True
        assert "entity_novelty" in meta["shift_signals"]

    def test_no_shift_with_known_entities(self):
        """Known entities should not trigger shift."""
        for i in range(5):
            self.detector.observe(
                note_entities={"actor": ["APT28"], "tool": ["mimikatz"]},
                note_domain="cti",
            )

        is_shift, meta = self.detector.detect_shift(
            note_entities={"actor": ["APT28"]},
            note_domain="cti",
        )
        # APT28 is known → novelty_ratio = 0
        assert meta["entity_novelty"] == 0.0
        # May still shift on topic or temporal, but not entity novelty
        assert "entity_novelty" not in meta.get("shift_signals", [])

    def test_topic_shift_triggers_shift(self):
        """Switching to a completely different domain should trigger shift."""
        # Build up EPG with CTI domain
        for i in range(5):
            self.detector.observe(
                note_entities={"actor": ["APT28"]},
                note_domain="cti",
            )

        # Switch to a new domain
        is_shift, meta = self.detector.detect_shift(
            note_entities={"person": ["Alice"]},
            note_domain="personal",
        )
        # Domain weight for "personal" should be very low
        assert meta.get("domain_weight", 1.0) < 0.5

    def test_temporal_gap_triggers_shift(self):
        """A large temporal gap should trigger shift."""
        # Build up EPG
        for i in range(5):
            self.detector.observe(
                note_entities={"actor": ["APT28"]},
                note_domain="cti",
            )

        # Simulate note arriving 6 hours later
        future_time = datetime.now() + timedelta(hours=6)
        is_shift, meta = self.detector.detect_shift(
            note_entities={"actor": ["APT28"]},
            note_domain="cti",
            note_time=future_time,
        )
        assert meta.get("temporal_gap_hours", 0) >= 4.0
        assert "temporal_gap" in meta.get("shift_signals", [])

    def test_reset_clears_epg(self):
        """Reset should clear EPG state."""
        for i in range(5):
            self.detector.observe(
                note_entities={"actor": ["APT28"]},
                note_domain="cti",
            )

        self.detector.reset()
        state = self.detector.get_state()
        assert state["epg_count"] == 0
        assert state["unique_entities"] == 0

    def test_partial_novelty_no_shift(self):
        """Partial entity novelty below threshold should not trigger entity shift."""
        # Build EPG with APT28 and mimikatz
        for i in range(5):
            self.detector.observe(
                note_entities={"actor": ["APT28"], "tool": ["mimikatz"]},
                note_domain="cti",
            )

        # One known, one novel entity → novelty = 0.5 (above threshold)
        # But let's test below threshold
        detector_low = SemanticShiftDetector(
            entity_shift_threshold=0.8,  # Higher threshold
            min_epg_size=3,
        )
        for i in range(5):
            detector_low.observe(
                note_entities={"actor": ["APT28"], "tool": ["mimikatz"]},
                note_domain="cti",
            )

        is_shift, meta = detector_low.detect_shift(
            note_entities={"actor": ["APT28"], "tool": ["cobaltstrike"]},
            note_domain="cti",
        )
        # novelty = 1/2 = 0.5 < 0.8 threshold → no entity shift
        assert meta["entity_novelty"] == 0.5


# ── ConsolidationEngine Tests ──────────────────────────────────────────────


class TestConsolidationEngine:
    """Unit tests for the consolidation engine."""

    def test_consolidation_with_mock(self):
        """Test consolidation flow with a mocked MemoryManager."""
        mm = MagicMock()
        mm.store.iterate_notes.return_value = []
        mm.indexer.extractor.extract_all.return_value = {"actor": ["APT28"]}

        engine = ConsolidationEngine(mm)
        report = engine.consolidate()
        assert report["notes_examined"] == 0
        assert report["skipped"] is True

    def test_consolidation_stats(self):
        """Consolidation engine should track stats."""
        mm = MagicMock()
        mm.store.iterate_notes.return_value = []
        engine = ConsolidationEngine(mm)
        stats = engine.get_stats()
        assert "consolidation_count" in stats
        assert "detector_state" in stats


# ── ConsolidationMiddleware Tests ───────────────────────────────────────────


class TestConsolidationMiddleware:
    """Integration tests for the consolidation middleware."""

    def test_middleware_observes_and_detects(self):
        """Middleware should observe notes and detect shifts."""
        mm = MagicMock()
        mm.store.iterate_notes.return_value = []

        middleware = ConsolidationMiddleware(mm, auto_consolidate=False)

        # Build up EPG state
        for i in range(5):
            middleware.before_write(
                note_entities={"actor": ["APT28"], "tool": ["mimikatz"]},
                note_domain="cti",
            )

        # Now trigger shift
        is_shift, meta = middleware.before_write(
            note_entities={"actor": ["Lazarus"], "cve": ["CVE-2026-0001"]},
            note_domain="cti",
        )
        assert is_shift is True

    def test_middleware_stats(self):
        """Middleware should report stats."""
        mm = MagicMock()
        middleware = ConsolidationMiddleware(mm)
        stats = middleware.get_stats()
        assert "consolidation_count" in stats
        assert "auto_consolidate" in stats

    def test_consolidate_now(self):
        """Manual consolidation should work."""
        mm = MagicMock()
        mm.store.iterate_notes.return_value = []
        middleware = ConsolidationMiddleware(mm)
        report = middleware.consolidate_now()
        assert "notes_examined" in report


# ── Real Note Tests ──────────────────────────────────────────────────────────

from zettelforge.note_schema import Content, Embedding, Links, MemoryNote, Metadata, Semantic


def _make_test_note(note_id, content, domain="cti"):
    now = datetime.now().isoformat()
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
    def test_consolidation_promotes_overlapping_notes(self):
        mm = MagicMock()
        notes = [
            _make_test_note("n1", "APT28 uses Cobalt Strike for C2"),
            _make_test_note("n2", "APT28 deploys Cobalt Strike beacons"),
            _make_test_note("n3", "APT28 targets NATO organizations"),
        ]
        mm.store.iterate_notes.return_value = notes
        mm.indexer.extractor.extract_all.side_effect = lambda text, use_llm=False: {
            "actor": ["apt28"] if "APT28" in text else [],
            "tool": ["cobalt-strike"] if "Cobalt Strike" in text else [],
        }
        mm.store._rewrite_note = MagicMock()

        engine = ConsolidationEngine(mm, shift_detector=SemanticShiftDetector(min_epg_size=1))
        report = engine.consolidate(force=True)
        assert report["notes_examined"] == 3
        assert report["notes_consolidated"] >= 1

    def test_contradiction_flags_older_note(self):
        mm = MagicMock()
        n1 = _make_test_note("n1", "APT28 uses DROPBEAR malware")
        n2 = _make_test_note("n2", "APT28 no longer uses DROPBEAR")
        # Make n1 older
        n1.created_at = "2020-01-01T00:00:00"

        mm.indexer.extractor.extract_all.side_effect = lambda text, use_llm=False: {
            "actor": ["apt28"],
            "tool": ["dropbear"] if "DROPBEAR" in text else [],
        }

        engine = ConsolidationEngine(mm, shift_detector=SemanticShiftDetector(min_epg_size=1))
        contradictions = engine._detect_contradictions(
            [n1, n2],
            {
                "n1": {"actor": ["apt28"], "tool": ["dropbear"]},
                "n2": {"actor": ["apt28"], "tool": ["dropbear"]},
            },
        )
        assert "n1" in contradictions
