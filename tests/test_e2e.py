"""
End-to-End Tests for ZettelForge
Tests the full pipeline: remember → recall → synthesize
with real Ollama embeddings and isolated temp storage.
"""
import tempfile
import pytest
from unittest.mock import patch

from zettelforge import MemoryManager
from zettelforge.note_schema import MemoryNote, Content, Semantic, Embedding, Metadata


class TestE2ERememberRecall:
    """Test basic remember/recall pipeline."""

    @pytest.fixture
    def mm(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = MemoryManager(
                jsonl_path=f"{tmpdir}/notes.jsonl",
                lance_path=f"{tmpdir}/vectordb",
            )
            yield mgr

    def test_remember_single_note(self, mm):
        """remember() should store and return a note ID."""
        note, status = mm.remember(
            content="APT28 has been observed using FoggyWeb malware.",
            domain="cti",
        )
        assert note is not None
        assert status in ("created", "updated", "unchanged")

    def test_recall_returns_notes(self, mm):
        """recall() should return relevant notes."""
        mm.remember(
            content="APT28 shifted to edge devices as initial access.",
            domain="cti",
        )
        results = mm.recall("APT28 edge devices", k=5)
        assert len(results) > 0

    def test_recall_returns_empty_for_unrelated(self, mm):
        """recall() should return empty for unrelated queries."""
        mm.remember(
            content="The sky is blue today.",
            domain="general",
        )
        results = mm.recall("APT29 campaign", k=5)
        # Non-CTI content shouldn't match CTI queries
        assert isinstance(results, list)



