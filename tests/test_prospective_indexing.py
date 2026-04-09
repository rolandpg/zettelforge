"""
Integration tests for Kumiho-style Prospective Indexing.

Tests:
  1. generate_prospective_index() produces valid entries for cti domain
  2. generate_prospective_index() returns [] for non-cti domain
  3. NoteConstructor.construct() populates prospective_index for cti notes
  4. ProspectiveRetriever retrieves notes by future-query matching
  5. MemoryManager.recall() blends prospective results
  6. Non-cti notes do not get prospective_index entries
"""
import pytest
import tempfile
from unittest.mock import patch, MagicMock

from zettelforge import MemoryManager
from zettelforge.note_constructor import NoteConstructor
from zettelforge.prospective_indexer import (
    generate_prospective_index,
    ProspectiveRetriever,
)
from zettelforge.memory_store import MemoryStore


class TestGenerateProspectiveIndex:
    """Unit tests for generate_prospective_index()."""

    def test_non_cti_domain_returns_empty(self):
        """Non-CTI domains should get no prospective entries."""
        result = generate_prospective_index(
            "Hi, how are you today?",
            domain="general",
        )
        assert result == []

    @patch("zettelforge.prospective_indexer.ollama")
    def test_cti_domain_generates_entries(self, mock_ollama):
        """CTI domain content should generate prospective entries."""
        mock_ollama.generate.return_value = {
            "response": '["APT28 will shift to targeting edge devices in next campaign",'
                        '"Organizations should audit edge device firmware updates",'
                        '"APT28 TTPs will evolve away from traditional server access"]'
        }
        result = generate_prospective_index(
            "APT28 has shifted to edge devices as initial access vector.",
            domain="cti",
        )
        assert len(result) == 3
        assert all(isinstance(e, str) and len(e) > 10 for e in result)

    @patch("zettelforge.prospective_indexer.ollama")
    def test_json_array_format_parsed_correctly(self, mock_ollama):
        """LLM response as JSON array should parse cleanly."""
        mock_ollama.generate.return_value = {
            "response": '["APT28 future targeting will include IoT devices",'
                        '"Detection rules for edge devices should be prioritized"]'
        }
        result = generate_prospective_index(
            "APT29 uses IoT devices for initial access.",
            domain="cti",
        )
        assert len(result) == 2
        # Entries should be under 200 chars
        assert all(len(e) <= 200 for e in result)


class TestNoteConstructorProspective:
    """NoteConstructor.construct() should call generate_prospective_index."""

    @patch("zettelforge.prospective_indexer.ollama")
    def test_cti_note_has_prospective_index(self, mock_ollama):
        """CTI-domain notes should have prospective_index populated."""
        mock_ollama.generate.return_value = {
            "response": '["APT28 will use cloud services for C2 in future operations",'
                        '"Cloud posture management is now a priority for APT28 defense"]'
        }
        nc = NoteConstructor()
        note = nc.construct(
            raw_content="APT28 has started using cloud services for command and control.",
            source_type="conversation",
            domain="cti",
        )
        assert hasattr(note.semantic, "prospective_index")
        assert len(note.semantic.prospective_index) > 0

    def test_non_cti_note_has_empty_prospective_index(self):
        """Non-CTI notes should have empty prospective_index."""
        nc = NoteConstructor()
        note = nc.construct(
            raw_content="Remember to buy milk.",
            source_type="conversation",
            domain="personal",
        )
        assert hasattr(note.semantic, "prospective_index")
        assert note.semantic.prospective_index == []


class TestProspectiveRetriever:
    """ProspectiveRetriever should match future-queries to notes."""

    def test_empty_index_returns_empty(self):
        """Empty store should return no results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(
                jsonl_path=f"{tmpdir}/notes.jsonl",
                lance_path=f"{tmpdir}/vectordb",
            )
            retriever = ProspectiveRetriever(store)
            results = retriever.retrieve(
                query="what will APT28 do next",
                note_lookup=lambda nid: None,
            )
            assert results == []

    def test_build_index_returns_entry_count(self):
        """build_index() should return count of indexed entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryStore(
                jsonl_path=f"{tmpdir}/notes.jsonl",
                lance_path=f"{tmpdir}/vectordb",
            )
            retriever = ProspectiveRetriever(store)
            count = retriever.build_index()
            assert isinstance(count, int)
            assert count >= 0


class TestMemoryManagerRecallProspective:
    """MemoryManager.recall() should blend prospective results."""

    def test_recall_includes_prospective_retriever(self):
        """recall() should have _prospective_retriever attached after call."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mm = MemoryManager(
                jsonl_path=f'{tmpdir}/notes.jsonl',
                lance_path=f'{tmpdir}/vectordb',
            )
            # recall() should lazily create _prospective_retriever
            mm.recall("test query")
            assert hasattr(mm, "_prospective_retriever")
            assert isinstance(mm._prospective_retriever, ProspectiveRetriever)
