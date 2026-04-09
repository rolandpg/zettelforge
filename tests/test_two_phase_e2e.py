"""End-to-end tests for Mem0-style two-phase pipeline."""
import pytest
import tempfile
from unittest.mock import patch

from zettelforge import MemoryManager


@pytest.fixture
def fresh_mm():
    tmpdir = tempfile.mkdtemp()
    return MemoryManager(
        jsonl_path=f"{tmpdir}/notes.jsonl",
        lance_path=f"{tmpdir}/vectordb",
    )


class TestRememberWithExtraction:
    @patch("zettelforge.fact_extractor.ollama")
    def test_extracts_and_stores_facts(self, mock_ollama, fresh_mm):
        mock_ollama.generate.return_value = {
            "response": '[{"fact": "APT28 shifted to edge devices", "importance": 8}, {"fact": "DROPBEAR no longer in use", "importance": 7}]'
        }
        results = fresh_mm.remember_with_extraction(
            "APT28 has shifted tactics. They no longer use DROPBEAR and now exploit edge devices.",
            domain="cti",
        )
        assert len(results) >= 1
        for note, status in results:
            assert status in ("added", "updated", "deleted", "noop")
            if status != "noop":
                assert note is not None

    @patch("zettelforge.fact_extractor.ollama")
    def test_returns_empty_for_low_importance(self, mock_ollama, fresh_mm):
        mock_ollama.generate.return_value = {
            "response": '[{"fact": "greeting exchanged", "importance": 1}]'
        }
        results = fresh_mm.remember_with_extraction(
            "Hi, how are you?",
            domain="general",
            min_importance=3,
        )
        assert len(results) == 0

    @patch("zettelforge.memory_updater.ollama")
    @patch("zettelforge.fact_extractor.ollama")
    def test_update_supersedes_old_note(self, mock_fact_ollama, mock_updater_ollama, fresh_mm):
        old_note, _ = fresh_mm.remember("APT28 uses DROPBEAR malware", domain="cti")

        mock_fact_ollama.generate.return_value = {
            "response": '[{"fact": "APT28 no longer uses DROPBEAR", "importance": 9}]'
        }
        mock_updater_ollama.generate.return_value = {
            "response": '{"operation": "UPDATE", "reason": "refines old intel"}'
        }
        results = fresh_mm.remember_with_extraction(
            "APT28 has dropped DROPBEAR from their toolkit.",
            domain="cti",
        )
        assert len(results) == 1
        new_note, status = results[0]
        assert status == "updated"
        refreshed_old = fresh_mm.store.get_note_by_id(old_note.id)
        assert refreshed_old.links.superseded_by == new_note.id

    @patch("zettelforge.memory_updater.ollama")
    @patch("zettelforge.fact_extractor.ollama")
    def test_noop_stores_nothing_new(self, mock_fact_ollama, mock_updater_ollama, fresh_mm):
        fresh_mm.remember("APT28 targets NATO", domain="cti")
        initial_count = fresh_mm.store.count_notes()

        mock_fact_ollama.generate.return_value = {
            "response": '[{"fact": "APT28 targets NATO", "importance": 6}]'
        }
        mock_updater_ollama.generate.return_value = {
            "response": '{"operation": "NOOP", "reason": "already stored"}'
        }
        results = fresh_mm.remember_with_extraction(
            "APT28 targets NATO allies.",
            domain="cti",
        )
        assert len(results) == 1
        assert results[0][1] == "noop"
        assert fresh_mm.store.count_notes() == initial_count

    def test_method_exists(self, fresh_mm):
        assert callable(getattr(fresh_mm, "remember_with_extraction", None))
